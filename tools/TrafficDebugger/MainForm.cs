using Accord.Video.FFMPEG;
using DotImaging;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using static System.Net.Mime.MediaTypeNames;
using static System.Windows.Forms.VisualStyles.VisualStyleElement.TextBox;
using Application = System.Windows.Forms.Application;
using Image = System.Drawing.Image;
using TrafficDebugger.Properties;

namespace TrafficDebugger
{
    public partial class MainForm : Form
    {
        class CarToDraw
        {
            public int carID;
            public int carStyle;
            public string roadSegmentSubsetName;
            public int roadSegmentOffset;
            public int carLengthInFeet;
        }

        private System.Windows.Forms.Timer _refreshTimer = null;
        private Dictionary<string, int> _roadSegmentOriginByName = new Dictionary<string, int>();
        private Dictionary<string, int> _roadSegmentLaneOffset = new Dictionary<string, int>();
        private Dictionary<string, string> _roadSegmentOrientationByName = new Dictionary<string, string>();
        //private Dictionary<string, int> _signalChangeCountByName = new Dictionary<string, int>();
        private Dictionary<int, Point> _carTurnStartingPoint = new Dictionary<int, Point>();
        private Dictionary<int, Point> _carLastDrawnPos = new Dictionary<int, Point>();
        private Dictionary<int, string> _carLastDirection = new Dictionary<int, string>();
        private Image _blankBackgroundImage = null;
        private object _lockObj = new object();
        private Image _workingImage = null;
        private Dictionary<string, object> _filenamesProcessedList = new Dictionary<string, object>();
        private bool _isClosing = false;
        private Font _avgSpeedFont = null;
        private Font _avgSpeedFontBold = null;
        private Brush _avgSpeedBrush = null;
        private Graphics _graphics = null;//
        //private string _intersectionType = "Stock";
        private string _intersectionType = "ML";
        private string _basePath;
        private string _basePathReverse;

        public MainForm()
        {
            InitializeComponent();
        }

        private void Form1_Load(object sender, EventArgs e)
        {
            this.Left = Math.Max(this.Left, Settings.Default.formX);
            this.Top = Math.Max(this.Top, Settings.Default.formY);
            //this.Width = Math.Max(this.Width, Settings.Default.formWidth);
            //this.Height = Math.Max(this.Height, Settings.Default.formHeight);
            this.intersectionTypeComboBox.Text = Settings.Default.intersectionType;
            this.checkBox1.Checked = Settings.Default.relativeStats;
            this.checkBox2.Checked = Settings.Default.showPercentages;
            this.checkBox3.Checked = Settings.Default.showWeights;

            this.Width += this.Width % 2;
            this.Height += this.Height % 2;
        }

        private void setRoadSegmentMetaData_VerticalRoad(string subSegmentName, int roadSegmentOriginY, int laneStartX)
        {
            _roadSegmentOriginByName[subSegmentName] = roadSegmentOriginY;
            _roadSegmentOrientationByName[subSegmentName] = "V";

            if (subSegmentName.Contains("north"))
            {
                _roadSegmentLaneOffset[subSegmentName + "/L1"] = laneStartX + 11;
                _roadSegmentLaneOffset[subSegmentName + "/L2"] = laneStartX;
                _roadSegmentLaneOffset[subSegmentName + "/T"] = laneStartX - 12;
                _roadSegmentLaneOffset[subSegmentName + "/L3"] = _roadSegmentLaneOffset[subSegmentName + "/T"];
            }
            else if (subSegmentName.Contains("south"))
            {
                _roadSegmentLaneOffset[subSegmentName + "/L1"] = laneStartX;
                _roadSegmentLaneOffset[subSegmentName + "/L2"] = laneStartX + 12;
                _roadSegmentLaneOffset[subSegmentName + "/T"] = laneStartX + 24;
                _roadSegmentLaneOffset[subSegmentName + "/L3"] = _roadSegmentLaneOffset[subSegmentName + "/T"];
            }
        }

        private void setRoadSegmentMetaData_HorizontalRoad(string subSegmentName, int roadSegmentOriginX, int laneStartY)
        {
            _roadSegmentOriginByName[subSegmentName] = roadSegmentOriginX;
            _roadSegmentOrientationByName[subSegmentName] = "H";

            if (subSegmentName.Contains("east"))
            {
                _roadSegmentLaneOffset[subSegmentName + "/L1"] = laneStartY + 12;
                _roadSegmentLaneOffset[subSegmentName + "/L2"] = laneStartY;
                _roadSegmentLaneOffset[subSegmentName + "/T"] = laneStartY - 12;
                _roadSegmentLaneOffset[subSegmentName + "/L3"] = _roadSegmentLaneOffset[subSegmentName + "/T"];
            }
            else if (subSegmentName.Contains("west"))
            {
                _roadSegmentLaneOffset[subSegmentName + "/L1"] = laneStartY;
                _roadSegmentLaneOffset[subSegmentName + "/L2"] = laneStartY + 12;
                _roadSegmentLaneOffset[subSegmentName + "/T"] = laneStartY + 24;
                _roadSegmentLaneOffset[subSegmentName + "/L3"] = _roadSegmentLaneOffset[subSegmentName + "/T"];
            }
        }

        private void refreshTimer_Tick(object sender, EventArgs e)
        {
            // Stop time to avoid "bunching"
            if (_refreshTimer != null)
            {
                _refreshTimer.Stop();
            }

            try
            {
                Console.WriteLine("Creating frames from debug info");
                while (true)
                {
                    List<string> currentFileList = new List<string>(Directory.GetFiles(_basePath + @"runtime_stats\\sim_snapshot_animation_data", "debug_frame_*.txt"));
                    currentFileList.Sort();

                    // Find the file we'll be working on.
                    string filename = null;

                    foreach (string currentFile in currentFileList)
                    {
                        if (!_filenamesProcessedList.ContainsKey(currentFile))
                        {
                            filename = currentFile;
                            break;
                        }
                    }

                    if (filename == null)
                    {
                        return;
                    }

                    _filenamesProcessedList[filename] = new object();

                    // Load up our car metadata.
                    if (_isClosing)
                    {
                        return;
                    }

                    if (_workingImage != null)
                    {
                        _workingImage.Dispose();
                    }

                    /*makeAvi(_basePath + "animation_frames\\",
                            _basePath + $"\\Animation_of_IntersectionType_{_intersectionType}.avi",
                            this.Width,
                            996, //this.Height,
                            15f,
                            "*.png");*/

                    // Start with a fresh background image.
                    try
                    {
                        lock (_lockObj)
                        {
                            _workingImage = new Bitmap((Image)_blankBackgroundImage.Clone());
                        }

                        string[] carMetadataLine = File.ReadAllLines(filename);
                        DateTime simTime = DateTime.Parse(carMetadataLine[0]);
                        dtLabel.Text = simTime.ToString("h:mm:sstt").ToLower();
                        _graphics = Graphics.FromImage(_workingImage);
                        drawZones();

                        // Load corresponding stats.
                        int hour24 = int.Parse(simTime.ToString("HH"));
                        string simTimestamp = $"{hour24}_{simTime.Minute}_{simTime.Second}";

                        intersectionCrossingStatsTextBox.SuspendLayout();
                        intersectionCrossingStatsTextBox.Text = getSnapshotData($"runtime_stats\\sim_snapshot_car_crossings\\day_summary_{simTimestamp}.txt", checkBox1.Checked, checkBox2.Checked);
                        intersectionCrossingStatsTextBox.ResumeLayout();

                        carCountStatsTextBox.SuspendLayout();
                        carCountStatsTextBox.Text = getSnapshotData($"runtime_stats\\sim_congestion\\day_summary_{simTimestamp}.txt", checkBox1.Checked, checkBox2.Checked);
                        carCountStatsTextBox.ResumeLayout();

                        carsToLetCrossTextBox.SuspendLayout();
                        carsToLetCrossTextBox.Text = getSnapshotData($"runtime_stats\\sim_snapshot_cars_on_road\\day_summary_{simTimestamp}.txt", checkBox1.Checked, checkBox2.Checked);
                        carsToLetCrossTextBox.ResumeLayout();

                        textBox1.SuspendLayout();
                        textBox1.Text = getSnapshotData($"runtime_stats\\sim_snapshot_travel_time\\day_summary_{simTimestamp}.txt", checkBox1.Checked, checkBox2.Checked);
                        textBox1.ResumeLayout();

                        textBox2.SuspendLayout();
                        textBox2.Text = getSnapshotData($"runtime_stats\\sim_snapshot_light_change_count\\day_summary_{simTimestamp}.txt", checkBox1.Checked, checkBox2.Checked);
                        textBox2.ResumeLayout();

                        //for (int idx = 0; idx < Math.Min(2, carMetadataLine.Length); idx++)
                        List<CarToDraw> carsToDrawList = new List<CarToDraw>();

                        for (int idx = 0; idx < carMetadataLine.Length; idx++)
                        //Parallel.For(0, carMetadataLine.Length, delegate (int idx)
                        {
                            try
                            {
                                if (intersectionTypeComboBox.Enabled == true)
                                {
                                    return;
                                }

                                string carDataLine = carMetadataLine[idx];
                                string carDataLineAdj = carDataLine.Replace(" ", "");
                                string[] carData = carDataLineAdj.Split(new char[] { ',' }, StringSplitOptions.None);

                                if (carDataLine.StartsWith("I"))
                                {
                                    string intersectionName = carData[0];

                                    //if (intersectionName != "I5")
                                    {
                                        //  continue;
                                    }

                                    string northSegment = carData[1];
                                    string southDegment = carData[2];
                                    string eastSegment = carData[3];
                                    string westSegment = carData[4];

                                    bool northMainGreen = carData[5].Trim() == "green";
                                    bool northTurnGreen = carData[6].Trim() == "green";
                                    bool southMainGreen = carData[7].Trim() == "green";
                                    bool southTurnGreen = carData[8].Trim() == "green";
                                    bool eastMainGreen = carData[9].Trim() == "green";
                                    bool eastTurnGreen = carData[10].Trim() == "green";
                                    bool westMainGreen = carData[11].Trim() == "green";
                                    bool westTurnGreen = carData[12].Trim() == "green";

                                    double avgSpeedNorthbound = double.Parse(carData[13].Trim());
                                    double avgSpeedSouthbound = double.Parse(carData[14].Trim());
                                    double avgSpeedEastbound = double.Parse(carData[15].Trim());
                                    double avgSpeedWestbound = double.Parse(carData[16].Trim());
                                    double avgCarsPerHour = double.Parse(carData[17].Trim());
                                    double maxCarsPerMinute = double.Parse(carData[18].Trim());
                                    int totalSignalChanges = int.Parse(carData[19].Trim());
                                    int totalCrossingsAtThisIntersection = int.Parse(carData[20].Trim());

                                    /*double frustrationFromNorth = carData[21] == "None" ? 0 : double.Parse(carData[21].Trim()) * 100;
                                    double frustrationFromSouth = carData[22] == "None" ? 0 : double.Parse(carData[22].Trim()) * 100;
                                    double frustrationFromEast = carData[23] == "None" ? 0 : double.Parse(carData[23].Trim()) * 100;
                                    double frustrationFromWest = carData[24] == "None" ? 0 : double.Parse(carData[24].Trim()) * 100;

                                    frustrationFromNorth = Math.Max(0, Math.Round(frustrationFromNorth, 1));
                                    frustrationFromSouth = Math.Max(0, Math.Round(frustrationFromSouth, 1));
                                    frustrationFromEast = Math.Max(0, Math.Round(frustrationFromEast, 1));
                                    frustrationFromWest = Math.Max(0, Math.Round(frustrationFromWest, 1));
                                    
                                    frustrationFromNorth = Math.Min(100, frustrationFromNorth);
                                    frustrationFromSouth = Math.Min(100, frustrationFromSouth);
                                    frustrationFromEast = Math.Min(100, frustrationFromEast);
                                    frustrationFromWest = Math.Min(100, frustrationFromWest);*/

                                    double frustrationFromNorth = carData[21] == "None" ? 0 : Math.Round(double.Parse(carData[21].Trim()), 1);
                                    double frustrationFromSouth = carData[22] == "None" ? 0 : Math.Round(double.Parse(carData[22].Trim()), 1);
                                    double frustrationFromEast = carData[23] == "None" ? 0 : Math.Round(double.Parse(carData[23].Trim()), 1);
                                    double frustrationFromWest = carData[24] == "None" ? 0 : Math.Round(double.Parse(carData[24].Trim()), 1);

                                    /*string weightFromNorth = carData[25];
                                    string weightFromSouth = carData[26];
                                    string weightFromEast = carData[27];
                                    string weightFromWest = carData[28];*/
                                    string weightFromNorth = Math.Round(double.Parse(carData[25]), 3).ToString();
                                    string weightFromSouth = Math.Round(double.Parse(carData[26]), 3).ToString();
                                    string weightFromEast = Math.Round(double.Parse(carData[27]), 3).ToString();
                                    string weightFromWest = Math.Round(double.Parse(carData[28]), 3).ToString();
                                    string carsToAllow = carData[30].ToString();

                                    string northSubsegment = northSegment + "/north";
                                    string southSubsegment = southDegment + "/south";
                                    string eastSubsegment = eastSegment + "/east";
                                    string westSubsegment = westSegment + "/west";

                                    drawStopLight(northSubsegment, northMainGreen, northTurnGreen);
                                    drawStopLight(southSubsegment, southMainGreen, southTurnGreen);
                                    drawStopLight(eastSubsegment, eastMainGreen, eastTurnGreen);
                                    drawStopLight(westSubsegment, westMainGreen, westTurnGreen);

                                    //drawAvgSpeedWatermark(intersectionName, northSubsegment, -65, -110, avgSpeedNorthbound);
                                    //drawAvgSpeedWatermark(intersectionName, southSubsegment, 50, 35, avgSpeedSouthbound);
                                    //drawAvgSpeedWatermark(intersectionName, eastSubsegment, 135, -170, avgSpeedEastbound);
                                    //drawAvgSpeedWatermark(intersectionName, westSubsegment, -65, +20, avgSpeedWestbound);

                                    //drawCarsPerMinuteWatermark(intersectionName, $"Intersection ID: {intersectionName}", 60, -160, southSubsegment);
                                    //drawCarsPerMinuteWatermark(intersectionName, $"Signal changes: {totalSignalChanges} ", 60, -140, southSubsegment);
                                    //drawCarsPerMinuteWatermark(intersectionName, $"Total Crossings: {totalCrossingsAtThisIntersection} ", 60, -120, southSubsegment);

                                    if (this._intersectionType == "ML")
                                    {
                                        if (this.checkBox3.Checked)
                                        {
                                            // Coming from the north, going south.
                                            double maxWeight = double.Parse(weightFromNorth);
                                            maxWeight = Math.Max(maxWeight, double.Parse(weightFromSouth));
                                            maxWeight = Math.Max(maxWeight, double.Parse(weightFromEast));
                                            maxWeight = Math.Max(maxWeight, double.Parse(weightFromWest));

                                            drawFrustrationFactor(intersectionName, $"Weight:\n{weightFromNorth}", double.Parse(weightFromNorth) == maxWeight, -135, -165, eastSubsegment);

                                            // Coming from the south, going north.
                                            drawFrustrationFactor(intersectionName, $"Weight:\n{weightFromSouth}", double.Parse(weightFromSouth) == maxWeight, 15, 105, eastSubsegment);

                                            // Coming from the east, going west.
                                            drawFrustrationFactor(intersectionName, $"Weight:\n{weightFromEast}", double.Parse(weightFromEast) == maxWeight, 85, -90, eastSubsegment);

                                            // Coming from the west, going east.
                                            drawFrustrationFactor(intersectionName, $"Weight:\n{weightFromWest}", double.Parse(weightFromWest) == maxWeight, -190, 25, eastSubsegment);
                                        }
                                        
                                        // Coming from the west, going east.
                                        drawCarsAllowed(intersectionName, carsToAllow);
                                        
                                    }

                                    //return;
                                    continue;
                                }

                                // Handle one car if it is valid.
                                if (carData.Length == 11)
                                {
                                    int carID = int.Parse(carData[0]);
                                    int carStyle = int.Parse(carData[1]);
                                    string roadSegmentName = carData[2];
                                    int laneID = int.Parse(carData[6]);
                                    int roadSegmentOffset = (int)double.Parse(carData[5]);
                                    int carLengthInFeet = (int)double.Parse(carData[4]);
                                    bool currentlyTurning = bool.Parse(carData[8]);
                                    double pctOfTurnCompleted = double.Parse(carData[9]);
                                    bool atIntersection = bool.Parse(carData[10]);

                                    string roadSegmentSubsetName = roadSegmentName + "/L" + laneID;

                                    // Draw onto the background image.
                                    if (currentlyTurning)
                                    {
                                        drawCarAt_LeftTurn(carID, carStyle, pctOfTurnCompleted, roadSegmentSubsetName, roadSegmentOffset, carLengthInFeet);
                                    }
                                    else
                                    {
                                        //if (carID == 226650)
                                        {
                                            CarToDraw carToDraw = new CarToDraw();
                                            carToDraw.carID = carID;
                                            carToDraw.carStyle = carStyle;
                                            carToDraw.roadSegmentSubsetName = roadSegmentSubsetName;
                                            carToDraw.roadSegmentOffset = roadSegmentOffset;
                                            carToDraw.carLengthInFeet = carLengthInFeet;

                                            lock (carsToDrawList)
                                            {
                                                carsToDrawList.Add(carToDraw);
                                            }
                                        }

                                        _carTurnStartingPoint.Remove(carID);
                                    }
                                }

                                _filenamesProcessedList[filename] = new object();
                            }
                            catch (Exception ex)
                            {
                                Console.WriteLine(ex.Message);
                            }
                        }//);

                        drawCarAt(carsToDrawList.ToArray());

                        //Thread.Sleep(15);
                        pictureBox2.Image = _workingImage;

                        try
                        {
                            this.SuspendLayout();
                            this.pictureBox2.BringToFront();

                            using (var bmp = new Bitmap(this.Width, 996 /*this.Height*/))
                            {
                                this.DrawToBitmap(bmp, new Rectangle(0, 0, bmp.Width, 996)); // bmp.Height));
                                bmp.Save(Path.ChangeExtension(Path.Combine(_basePath + @"runtime_stats\visualizer_animation_frames", Path.GetFileName(filename)), ".png"));
                            }
                        }
                        finally
                        {
                            this.pictureBox2.SendToBack();
                            this.ResumeLayout();
                        }

                        Application.DoEvents();
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine(ex.Message);
                    }
                }
            }
            finally
            {
                if (_refreshTimer != null)
                {
                    _refreshTimer.Start();
                }
            }
        }

        private void drawCarAt(CarToDraw[] carToDrawList)
        {
            lock (_graphics)
            {
                foreach (CarToDraw car in carToDrawList)
                {
                    string roadSegmentName = car.roadSegmentSubsetName.Replace("/L1", "").Replace("/L2", "").Replace("/L3", "").Replace("/L0", "").Replace("/T", "");

                    // Find front bumper pos.
                    double pixelScaleFactor = (double)660 / 5280;  /* Scaled/Unscaled road segment length */;
                    int roadSegmentLengthScaled = (int)((double)5280 * pixelScaleFactor);

                    int roadSegmentStartPos = _roadSegmentOriginByName[roadSegmentName];
                    int roadSegmentOffsetScaled = (int)((double)car.roadSegmentOffset * pixelScaleFactor);

                    int absFrontBumperPos = 0;

                    if (roadSegmentName.Contains("east"))
                    {
                        absFrontBumperPos = roadSegmentStartPos + roadSegmentLengthScaled - roadSegmentOffsetScaled;
                    }
                    if (roadSegmentName.Contains("west"))
                    {
                        absFrontBumperPos = roadSegmentStartPos + roadSegmentOffsetScaled - 1;
                    }
                    else if (roadSegmentName.Contains("north"))
                    {
                        absFrontBumperPos = roadSegmentStartPos + roadSegmentOffsetScaled - 1;
                    }
                    else if (roadSegmentName.Contains("south"))
                    {
                        absFrontBumperPos = roadSegmentStartPos + roadSegmentLengthScaled - roadSegmentOffsetScaled;
                    }

                    // Find Y coordinate of our lane on this sub-segment.
                    int absYLanePos = _roadSegmentLaneOffset[car.roadSegmentSubsetName];

                    if (roadSegmentName.Contains("north") && car.roadSegmentSubsetName.Contains("/T"))
                    {
                        absYLanePos -= 35;
                    }
                    else if (roadSegmentName.Contains("south") && car.roadSegmentSubsetName.Contains("/T"))
                    {
                        //absYLanePos += 5;
                    }

                    // Draw onto the background image.
                    Image carImage;

                    if (roadSegmentName.Contains("east"))
                    {
                        carImage = carRightImageList.Images[car.carStyle];
                        _carLastDirection[car.carID] = "east";
                    }
                    else if (roadSegmentName.Contains("west"))
                    {
                        carImage = carLeftImageList.Images[car.carStyle];
                        _carLastDirection[car.carID] = "west";
                    }
                    else if (roadSegmentName.Contains("south"))
                    {
                        carImage = carDownImageList.Images[car.carStyle];
                        _carLastDirection[car.carID] = "south";
                    }
                    else
                    {
                        carImage = carUpImageList.Images[car.carStyle];
                        _carLastDirection[car.carID] = "north";
                    }

                    double scaledPixelsPerFoot = car.carLengthInFeet * pixelScaleFactor;
                    double carPixels = Math.Max(1, car.carLengthInFeet * pixelScaleFactor);

                    //g.ScaleTransform((float)scaledPixelsPerFoot, (float)scaledPixelsPerFoot);

                    //Console.WriteLine(absYLanePos);

                    // Draw!
                    //lock (_graphics)
                    //using (Graphics g = Graphics.FromImage(_workingImage))
                    {
                        if (roadSegmentName.Contains("east") || roadSegmentName.Contains("west"))
                        {
                            _graphics.DrawImage(carImage, absFrontBumperPos, absYLanePos);
                            _carLastDrawnPos[car.carID] = new Point(absFrontBumperPos, absYLanePos);
                        }
                        else
                        {
                            _graphics.DrawImage(carImage, absYLanePos, absFrontBumperPos);
                            _carLastDrawnPos[car.carID] = new Point(absYLanePos, absFrontBumperPos);
                        }
                    }
                }
            }
        }

        private void drawCarAt_LeftTurn(int carID, int carStyle, double turnCompletionPct, string roadSegmentSubsetName, int roadSegmentOffset, int carLengthInFeet)
        {
            string roadSegmentName = roadSegmentSubsetName.Replace("/L1", "").Replace("/L2", "").Replace("/L3", "").Replace("/T", "");

            // Find front bumper pos.
            double pixelScaleFactor = (double)660 / 5280;  /* Scaled/Unscaled road segment length */;
            int roadSegmentLengthScaled = (int)((double)5280 * pixelScaleFactor);

            int roadSegmentStartPos = _roadSegmentOriginByName[roadSegmentName];
            int roadSegmentOffsetScaled = (int)((double)roadSegmentOffset * pixelScaleFactor);

            int absFrontBumperPos = 0;

            if (roadSegmentName.Contains("east"))
            {
                absFrontBumperPos = roadSegmentStartPos + roadSegmentLengthScaled - roadSegmentOffsetScaled;
            }
            else if (roadSegmentName.Contains("west"))
            {
                absFrontBumperPos = roadSegmentStartPos + roadSegmentLengthScaled;
            }
            else if (roadSegmentName.Contains("north"))
            {
                absFrontBumperPos = roadSegmentStartPos + roadSegmentOffsetScaled - 1;
            }
            else if (roadSegmentName.Contains("south"))
            {
                absFrontBumperPos = roadSegmentStartPos + roadSegmentLengthScaled - roadSegmentOffsetScaled;
            }

            // Find Y coordinate of our lane on this sub-segment.
            int absYLanePos = _roadSegmentLaneOffset[roadSegmentSubsetName];

            if (roadSegmentName.Contains("north") && roadSegmentSubsetName.Contains("/T"))
            {
                absYLanePos -= 35;
            }
            else if (roadSegmentName.Contains("south") && roadSegmentSubsetName.Contains("/T"))
            {
                //absYLanePos += 5;
            }

            // Draw onto the background image.
            Image carImage;
            float rotationAmt = 0f;

            if (_carLastDirection[carID].Contains("east"))
            {
                carImage = carRightImageList.Images[carStyle];
                rotationAmt = -(90 * (float)turnCompletionPct);
            }
            else if (_carLastDirection[carID].Contains("west"))
            {
                carImage = carLeftImageList.Images[carStyle];
                rotationAmt = 90 + (90 - (90 * (float)turnCompletionPct));
            }
            else if (_carLastDirection[carID].Contains("south"))
            {
                carImage = carDownImageList.Images[carStyle];
                rotationAmt = 180 - (90 * (float)turnCompletionPct);
            }
            else
            {
                carImage = carUpImageList.Images[carStyle];
                rotationAmt = 90 + (90 - (90 * (float)turnCompletionPct));
            }

            // Find where the turn started.
            Point startingPt;
            if (!_carTurnStartingPoint.ContainsKey(carID))
            {
                int xOffset = 0;
                int yOffset = 0;

                if (_carLastDirection[carID].Contains("north"))
                {
                    xOffset = 0;
                    yOffset = -5;
                }
                else if (_carLastDirection[carID].Contains("south"))
                {
                    xOffset = 0;
                    yOffset = 5;
                }
                else if (_carLastDirection[carID].Contains("east"))
                {
                    xOffset = -5;
                    yOffset = 0;
                }
                else
                {
                    xOffset = 5;
                    yOffset = 0;
                }

                _carTurnStartingPoint[carID] = new Point(_carLastDrawnPos[carID].X + xOffset, _carLastDrawnPos[carID].Y + yOffset);
            }
            startingPt = _carTurnStartingPoint[carID];

            // Find where the turn will end up.
            Point destPoint;

            if (roadSegmentName.Contains("east") || roadSegmentName.Contains("west"))
            {
                destPoint = new Point(absFrontBumperPos, absYLanePos);
            }
            else
            {
                destPoint = new Point(absYLanePos, absFrontBumperPos);
            }

            // Find the current point.
            double ptOffsetX = (double)(destPoint.X - startingPt.X) * turnCompletionPct;
            double ptOffsetY = (double)(destPoint.Y - startingPt.Y) * turnCompletionPct;

            Point currentPt = new Point((int)startingPt.X + (int)(ptOffsetX * turnCompletionPct),
                                        (int)startingPt.Y + (int)(ptOffsetY * turnCompletionPct));

            lock (_graphics)
            {
                Matrix m = _graphics.Transform;
                m.RotateAt(rotationAmt, currentPt);
                _graphics.Transform = m;

                // Draw!
                _graphics.DrawImage(carImage, currentPt);
                _graphics.ResetTransform();
            }
        }

        /*private void dumpPositionDebugInfo()
        {
            _workingImage = new Bitmap((Image)pictureBox2.Image.Clone());
            int roadSegmentIdx = 1;
            int carStyleID = 0;

            foreach (string segmentName in _roadSegmentOriginByName.Keys)
            {
                // Road segment name.
                drawCarAt(0, carStyleID, segmentName + "/L1", 5160, 8);
                drawCarAt(0, carStyleID, segmentName + "/L1", 0, 8);
                drawCarAt(0, carStyleID, segmentName + "/L2", 5160, 8);
                drawCarAt(0, carStyleID, segmentName + "/L2", 0, 8);
                drawCarAt(0, carStyleID, segmentName + "/T", 0, 8);

                roadSegmentIdx++;
                carStyleID = (carStyleID + 1) % 12;
            }

            pictureBox2.Image = _workingImage;
        }*/

        private void Form1_FormClosed(object sender, FormClosedEventArgs e)
        {
            Settings.Default.formX = this.Left;
            Settings.Default.formY = this.Top;
            Settings.Default.formWidth = this.Width;
            Settings.Default.formHeight = this.Height;
            Settings.Default.intersectionType = this.intersectionTypeComboBox.Text;
            Settings.Default.relativeStats = this.checkBox1.Checked;
            Settings.Default.showPercentages = this.checkBox2.Checked;
            Settings.Default.showWeights = this.checkBox3.Checked;
            Settings.Default.Save();
        }

        private void Form1_FormClosing(object sender, FormClosingEventArgs e)
        {
            _isClosing = true;
            if (_refreshTimer != null)
            {
                _refreshTimer.Stop();
            }

        }

        private void drawStopLight(string roadSubsegment, bool mainLightGreen, bool leftTurnLightGreen)
        {
            ImageList il;
            Point pt;

            if (roadSubsegment.Contains("north"))
            {
                pt = new Point(_roadSegmentLaneOffset[roadSubsegment + "/L1"] + 20, _roadSegmentOriginByName[roadSubsegment] + 740);
                il = imageList1;
            }
            else if (roadSubsegment.Contains("south"))
            {
                pt = new Point(_roadSegmentLaneOffset[roadSubsegment + "/L1"] - 35, _roadSegmentOriginByName[roadSubsegment] - 125);
                il = imageList3;
            }
            else if (roadSubsegment.Contains("east"))
            {
                pt = new Point(_roadSegmentOriginByName[roadSubsegment] - 120, _roadSegmentLaneOffset[roadSubsegment + "/L1"] + 20);
                il = imageList2;
            }
            else
            {
                pt = new Point(_roadSegmentOriginByName[roadSubsegment] + 730, _roadSegmentLaneOffset[roadSubsegment + "/L1"] - 35);
                il = imageList4;
            }

            int idx;

            string lightSpec = mainLightGreen ? "G" : "R";
            lightSpec += leftTurnLightGreen ? "G" : "R";

            switch (lightSpec)
            {
                case "GG":
                    idx = 1;
                    break;

                case "GR":
                    idx = 3;
                    break;

                case "RG":
                    idx = 2;
                    break;

                default:
                    idx = 0;
                    break;

            }

            lock (_graphics)
            {
                _graphics.DrawImage(il.Images[idx], pt);
            }
        }

        private void drawAvgSpeedWatermark(string intersectionName, string southboundRoadStripName, int xOffset, int yOffset, double avgSpeed)
        {
            int yPos = _roadSegmentOriginByName[southboundRoadStripName];
            int xPos = _roadSegmentLaneOffset[southboundRoadStripName + "/L1"];

            string avgSpeedStr = ((int)avgSpeed).ToString();

            lock (_graphics)
            {
                _graphics.DrawString(avgSpeedStr, _avgSpeedFont, _avgSpeedBrush, new Point(xPos + xOffset, yPos + yOffset));
            }
        }

        private void drawCarsPerMinuteWatermark(string intersectionName, string textToDraw, int xOffset, int yOffset, string southboundRoadStripName)
        {
            int yPos = _roadSegmentOriginByName[southboundRoadStripName];
            int xPos = _roadSegmentLaneOffset[southboundRoadStripName + "/L1"];

            lock (_graphics)
            {
                _graphics.DrawString(textToDraw, _avgSpeedFont, _avgSpeedBrush, new Point(xPos + xOffset, yPos + yOffset));
            }
        }

        private void drawFrustrationFactor(string intersectionName, string textToDraw, bool drawBold, int xOffset, int yOffset, string southboundRoadStripName, bool highlightPoint = false)
        {
            int yPos;
            int xPos;

            /*if (intersectionName == "I2")
            {
                //Console.WriteLine(textToDraw);
                textToDraw = "Yikes!";
            }*/

            if (_roadSegmentOrientationByName[southboundRoadStripName] == "H")
            {
                xPos = _roadSegmentOriginByName[southboundRoadStripName];
                yPos = _roadSegmentLaneOffset[southboundRoadStripName + "/L1"];
            }
            else
            {
                yPos = _roadSegmentOriginByName[southboundRoadStripName];
                xPos = _roadSegmentLaneOffset[southboundRoadStripName + "/L1"];

            }

            lock (_graphics)
            {
                int xFinal = xPos + xOffset;
                int yFinal = yPos + yOffset;

                //using (Brush br = drawBold ? _frustrationFactorBrushBold : _avgSpeedBrush)
                {
                    _graphics.DrawString(textToDraw, drawBold ? _avgSpeedFontBold : _avgSpeedFont, _avgSpeedBrush, new Point(xFinal, yFinal));
                    if (highlightPoint)
                    {
                        //_graphics.DrawRectangle(Pens.Red, xFinal, yFinal, 4, 4);
                    }
                }
            }
        }

        private void makeAvi(string imageInputfolderName,
                             string outVideoFileName,
                             int width,
                             int height,
                             float fps = 12.0f,
                             string imgSearchPattern = "*.png")
        {
            // create instance of video writer
            VideoFileWriter writer = new VideoFileWriter();

            // create new video file
            if (width % 2 == 1)          
            {
                width++;
            }

            writer.Open(outVideoFileName, width, 996, 20, VideoCodec.MPEG4, 7000000);

            // create a bitmap to save into the video file
            string[] imageFileList = Directory.GetFiles(imageInputfolderName, imgSearchPattern);
            int currentIdx = 0;

            foreach (string imageFilename in imageFileList)
            {
                try
                {
                    using (Bitmap bitmap = new Bitmap(imageFilename))
                    {
                        Bitmap roundedBmp = new Bitmap(bitmap.Width + bitmap.Width % 2, bitmap.Height + bitmap.Height % 2);
                        using (Graphics g2 = Graphics.FromImage(roundedBmp))
                        {
                            g2.DrawImage(bitmap, 0, 0, roundedBmp.Width, roundedBmp.Height);
                        }


                        // Sanity check.
                        //#if (bitmap.Width == width && bitmap.Height == height)
                        {

                            // save the image to the video file
                            writer.WriteVideoFrame(roundedBmp);

                            if (currentIdx++ % 250 == 0)
                            {
                                Console.WriteLine("Images added to animation: " + currentIdx);
                                Application.DoEvents();
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error writing frame {currentIdx} to video file: {ex.Message}");
                }

            }

            Console.WriteLine("Images added to animation: " + imageFileList.Length);
            writer.Close();
        }

        private void button1_Click(object sender, EventArgs e)
        {
            Console.WriteLine("Creating animation of frames");
            _basePath = @"C:\BWHacker2023\runtime_output\Intersection" + intersectionTypeComboBox.Text + @"\";
            makeAvi(_basePath + @"runtime_stats\visualizer_animation_frames\",
                    _basePath + $"\\Animation_of_IntersectionType_{_intersectionType}.avi",
                    this.Width,
                    this.Height,
                    15f,
                    "*.png");
        }

        private void goStopButton_Click(object sender, EventArgs e)
        {
            if (intersectionTypeComboBox.Enabled == false)
            {
                _refreshTimer.Stop();
                _refreshTimer.Dispose();

                intersectionTypeComboBox.Enabled = true;
                goStopButton.Text = "   Go!";
                goStopButton.ImageIndex = 0;

                return;
            }

            lock (_lockObj)
            {
                _blankBackgroundImage = new Bitmap((Image)pictureBox2.Image.Clone());
            }

            _intersectionType = intersectionTypeComboBox.Text;
            _basePath = @"C:\BWHacker2023\runtime_output\Intersection" + intersectionTypeComboBox.Text + @"\";
            _basePathReverse = @"C:\BWHacker2023\runtime_output\Intersection" + getReverseIntersectionType(intersectionTypeComboBox.Text) + @"\";

            int roadLevel1EastY = 157;
            int roadLevel1WestY = 120;
            int roadLevel2EastY = 885;
            int roadLevel2WestY = 848;
            int roadLevel3EastY = 1613;
            int roadLevel3WestY = 1576;

            int roadVertAxis1NorthX = 191;
            int roadVertAxis1SouthX = 154;
            int roadVertAxis2NorthX = 920;
            int roadVertAxis2SouthX = 885;
            int roadVertAxis3NorthX = 1650;
            int roadVertAxis3SouthX = 1615;

            // Set up road metadata.
            setRoadSegmentMetaData_HorizontalRoad("R4/east", -530, roadLevel1EastY);
            setRoadSegmentMetaData_HorizontalRoad("R4/west", -510, roadLevel1WestY);
            setRoadSegmentMetaData_HorizontalRoad("R5/east", 200, roadLevel1EastY);
            setRoadSegmentMetaData_HorizontalRoad("R5/west", 220, roadLevel1WestY);
            setRoadSegmentMetaData_HorizontalRoad("R6/east", 933, roadLevel1EastY);
            setRoadSegmentMetaData_HorizontalRoad("R6/west", 950, roadLevel1WestY);
            setRoadSegmentMetaData_HorizontalRoad("R7/east", 1658, roadLevel1EastY);
            setRoadSegmentMetaData_HorizontalRoad("R7/west", 1680, roadLevel1WestY);

            setRoadSegmentMetaData_HorizontalRoad("R11/east", -530, roadLevel2EastY);
            setRoadSegmentMetaData_HorizontalRoad("R11/west", -510, roadLevel2WestY);
            setRoadSegmentMetaData_HorizontalRoad("R12/east", 200, roadLevel2EastY);
            setRoadSegmentMetaData_HorizontalRoad("R12/west", 220, roadLevel2WestY);
            setRoadSegmentMetaData_HorizontalRoad("R13/east", 933, roadLevel2EastY);
            setRoadSegmentMetaData_HorizontalRoad("R13/west", 950, roadLevel2WestY);
            setRoadSegmentMetaData_HorizontalRoad("R14/east", 1658, roadLevel2EastY);
            setRoadSegmentMetaData_HorizontalRoad("R14/west", 1680, roadLevel2WestY);

            setRoadSegmentMetaData_HorizontalRoad("R18/east", -530, roadLevel3EastY);
            setRoadSegmentMetaData_HorizontalRoad("R18/west", -510, roadLevel3WestY);
            setRoadSegmentMetaData_HorizontalRoad("R19/east", 200, roadLevel3EastY);
            setRoadSegmentMetaData_HorizontalRoad("R19/west", 220, roadLevel3WestY);
            setRoadSegmentMetaData_HorizontalRoad("R20/east", 933, roadLevel3EastY);
            setRoadSegmentMetaData_HorizontalRoad("R20/west", 950, roadLevel3WestY);
            setRoadSegmentMetaData_HorizontalRoad("R21/east", 1658, roadLevel3EastY);
            setRoadSegmentMetaData_HorizontalRoad("R21/west", 1680, roadLevel3WestY);

            setRoadSegmentMetaData_VerticalRoad("R1/north", -541, roadVertAxis1NorthX);
            setRoadSegmentMetaData_VerticalRoad("R1/south", -564, roadVertAxis1SouthX);
            setRoadSegmentMetaData_VerticalRoad("R8/north", 185, roadVertAxis1NorthX);
            setRoadSegmentMetaData_VerticalRoad("R8/south", 165, roadVertAxis1SouthX);
            setRoadSegmentMetaData_VerticalRoad("R15/north", 913, roadVertAxis1NorthX);
            setRoadSegmentMetaData_VerticalRoad("R15/south", 893, roadVertAxis1SouthX);
            setRoadSegmentMetaData_VerticalRoad("R22/north", 1640, roadVertAxis1NorthX);
            setRoadSegmentMetaData_VerticalRoad("R22/south", 1620, roadVertAxis1SouthX);

            setRoadSegmentMetaData_VerticalRoad("R2/north", -541, roadVertAxis2NorthX);
            setRoadSegmentMetaData_VerticalRoad("R2/south", -564, roadVertAxis2SouthX);
            setRoadSegmentMetaData_VerticalRoad("R9/north", 185, roadVertAxis2NorthX);
            setRoadSegmentMetaData_VerticalRoad("R9/south", 163, roadVertAxis2SouthX);
            setRoadSegmentMetaData_VerticalRoad("R16/north", 913, roadVertAxis2NorthX);
            setRoadSegmentMetaData_VerticalRoad("R16/south", 890, roadVertAxis2SouthX);
            setRoadSegmentMetaData_VerticalRoad("R23/north", 1640, roadVertAxis2NorthX);
            setRoadSegmentMetaData_VerticalRoad("R23/south", 1620, roadVertAxis2SouthX);

            setRoadSegmentMetaData_VerticalRoad("R3/north", -541, roadVertAxis3NorthX);
            setRoadSegmentMetaData_VerticalRoad("R3/south", -564, roadVertAxis3SouthX);
            setRoadSegmentMetaData_VerticalRoad("R10/north", 185, roadVertAxis3NorthX);
            setRoadSegmentMetaData_VerticalRoad("R10/south", 163, roadVertAxis3SouthX);
            setRoadSegmentMetaData_VerticalRoad("R17/north", 913, roadVertAxis3NorthX);
            setRoadSegmentMetaData_VerticalRoad("R17/south", 890, roadVertAxis3SouthX);
            setRoadSegmentMetaData_VerticalRoad("R24/north", 1640, roadVertAxis3NorthX);
            setRoadSegmentMetaData_VerticalRoad("R24/south", 1620, roadVertAxis3SouthX);

            string[] filesToRemove = Directory.GetFiles(_basePath + @"\runtime_stats\visualizer_animation_frames\", " *.png", SearchOption.AllDirectories);
            foreach (string filename in filesToRemove)
            {
                File.Delete(filename);
            }

            //simTypeLabel.Text = _intersectionType;
            _filenamesProcessedList = new Dictionary<string, object>();

            _avgSpeedFont = new Font(this.Font.FontFamily, 11f);
            _avgSpeedFontBold = new Font(this.Font.FontFamily, 11f, FontStyle.Bold);
            _avgSpeedBrush = new SolidBrush(Color.White);

            intersectionTypeComboBox.Enabled = false;
            goStopButton.Text = "   Stop";
            goStopButton.ImageIndex = 1;

            _refreshTimer = new System.Windows.Forms.Timer();
            _refreshTimer.Interval = 5;
            _refreshTimer.Tick += refreshTimer_Tick;
            _refreshTimer.Start();

            //dumpPositionDebugInfo();
        }

        private string getReverseIntersectionType(string inputType)
        {
            if (inputType == "Stock")
            {
                return "ML";
            }
            else
            {
                return "Stock";
            }
        }

        private void checkBox1_CheckedChanged(object sender, EventArgs e)
        {

        }

        private string[,] getCsvAsCells(string csvText)
        {
            string csvTextMassaged = csvText;

            csvTextMassaged = csvTextMassaged.Replace("\r\n", "\n");

            for (int i = 0; i < 10; i++)
            {
                csvTextMassaged = csvTextMassaged.Replace("  ", " ");
            }

            csvTextMassaged = csvTextMassaged.Replace(" ", ",");
            csvTextMassaged = csvTextMassaged.Replace(",\n", "\n");

            if (csvTextMassaged.EndsWith("\n"))
            {
                csvTextMassaged = csvTextMassaged.Substring(0, csvTextMassaged.Length - 1);
            }

            // Break into lines.
            string[] allLines = csvTextMassaged.Split(new char[] { '\n' });
            int colCount = allLines[0].Split(new char[] { ',' }).Length;

            string[,] resultSet = new string[allLines.Length, colCount];
            for (int lineIdx = 0; lineIdx < allLines.Length; lineIdx++)
            {
                // Break out columns.
                string[] colsForLine = allLines[lineIdx].Split(new char[] { ',' });

                // Copy into the output cells.
                for (int colIdx = 0; colIdx < Math.Min(colsForLine.Length, colCount); colIdx++)
                {
                    resultSet[lineIdx, colIdx] = colsForLine[colIdx];
                }
            }

            for (int lineIdx = 0; lineIdx < resultSet.GetUpperBound(0); lineIdx++)
            {
                for (int colIdx = 0; colIdx < resultSet.GetUpperBound(1); colIdx++)
                {
                    if (resultSet[lineIdx, colIdx] == null)
                    {
                        resultSet[lineIdx, colIdx] = "";
                    }
                }
            }

            return resultSet;
        }

        private string computeDifference(string statsCsv, string statsCsvReference, bool showDiffsAsPercentages)
        {
            string[,] statsCells = getCsvAsCells(statsCsv);
            string[,] statsCellsReference = null;

            if (statsCsvReference != null)
            {
                statsCellsReference = getCsvAsCells(statsCsvReference);
            }

            // Perform a diff by cell.
            string[,] statsCellsDiff = new string[statsCells.GetLength(0), statsCells.GetLength(1)];
            for (int lineIdx = 0; lineIdx < statsCells.GetLength(0); lineIdx++)
            {
                for (int colIdx = 0; colIdx < statsCells.GetLength(1); colIdx++)
                {
                    int originalCellWidth = statsCells[1, colIdx].Length;

                    int statValue;
                    int statValueReverse;

                    if (statsCellsReference != null &&
                        int.TryParse(statsCells[lineIdx, colIdx], out statValue) &&
                        int.TryParse(statsCellsReference[lineIdx, colIdx], out statValueReverse))
                    {
                        int diffValue = statValue - statValueReverse;
                        string diffStr;

                        if (showDiffsAsPercentages)
                        {
                            if (statValueReverse == 0)
                            {
                                diffStr = "0";
                            }
                            else
                            {
                                diffStr = ((int)((double)diffValue / statValueReverse * 100)).ToString() + "%";
                            }
                        }
                        else
                        {
                            diffStr = diffValue.ToString();
                        }

                        statsCellsDiff[lineIdx, colIdx] = diffStr.PadLeft(originalCellWidth);
                    }
                    else
                    {
                        if (statsCells[lineIdx, colIdx] == null)
                        {
                            statsCellsDiff[lineIdx, colIdx] = "".PadLeft(originalCellWidth);
                        }
                        else
                        {
                            statsCellsDiff[lineIdx, colIdx] = statsCells[lineIdx, colIdx].PadLeft(originalCellWidth);
                        }
                    }
                }
            }

            // Convert to text compatible with the input format.
            string resultSet = "";
            for (int lineIdx = 0; lineIdx < statsCells.GetLength(0); lineIdx++)
            {
                for (int colIdx = 0; colIdx < statsCells.GetLength(1); colIdx++)
                {
                    resultSet += statsCellsDiff[lineIdx, colIdx] + " ";
                }

                resultSet = resultSet.TrimEnd();
                resultSet += "\r\n";
            }

            return resultSet;
        }

        private void crossingsStatsTextBox_TextChanged(object sender, EventArgs e)
        {

        }

        private string getSnapshotData(string relDataFilename, bool showValuesAsDiffs, bool showDiffAsPercentages)
        {
            string statsFilename = _basePath + relDataFilename;
            string finalResult = "";

            if (File.Exists(statsFilename))
            {
                // Load the reference data.
                string statsFilenameRef = _basePathReverse + relDataFilename;
                if (!File.Exists(statsFilenameRef))
                {
                    statsFilenameRef = statsFilename;
                }

                string statsText = File.ReadAllText(statsFilename);
                string statsTextRef = null;

                // Reference data only loaded if we are supposed to show
                // relative values for stats.
                if (showValuesAsDiffs)
                {
                    statsTextRef = File.ReadAllText(statsFilenameRef);
                    finalResult = computeDifference(statsText, statsTextRef, this.checkBox2.Checked);
                }
                else
                {
                    finalResult = statsText;
                }
            }

            return finalResult;
        }

        private void drawZones()
        {
            /*foreach (string subSegmentName in _roadSegmentOriginByName.Keys)
            {
                int lane1X = _roadSegmentLaneOffset[subSegmentName + "/L1"];
                int lane2X = _roadSegmentLaneOffset[subSegmentName + "/L2"];
                int roadSegmentOriginY = _roadSegmentOriginByName[subSegmentName];

                _graphics.DrawLine(Pens.White, lane1X, roadSegmentOriginY, lane2X + 20, roadSegmentOriginY);
            }*/
        }

        private void checkBox2_CheckedChanged(object sender, EventArgs e)
        {

        }

        private void drawCarsAllowed(string intersectionName, string carsToAllow)
        {
            int yPos;
            int xPos;

            if (intersectionName == "I1" || intersectionName == "I2" || intersectionName == "I3")
                yPos = 120;
            else if (intersectionName == "I4" || intersectionName == "I5" || intersectionName == "I6")
                yPos = 848;
            else
                yPos = 1576;

            if (intersectionName == "I1" || intersectionName == "I4" || intersectionName == "I7")
                xPos = 154;
            else if (intersectionName == "I2" || intersectionName == "I5" || intersectionName == "I8")
                xPos = 885;
            else
                xPos = 1615;

            yPos += 10;
            
            lock (_graphics)
            {
                Font f = new Font(this.Font.FontFamily, 20);

                SizeF size = _graphics.MeasureString(carsToAllow, f);

                xPos = (int)(xPos + 28) - (int)(size.Width / 2);
                _graphics.DrawString(carsToAllow, f, Brushes.White, xPos, yPos);
            }
        }

        private int scaleXPos(int originalXPos)
        {
            return (int)((double)originalXPos * (double)pictureBox2.Width / (double)_blankBackgroundImage.Width);
        }

        private int scaleYPos(int originalYPos)
        {
            return (int)((double)originalYPos * (double)pictureBox2.Height / (double)_blankBackgroundImage.Height);
        }

        private void button2_Click(object sender, EventArgs e)
        {
            panel2.Visible = !panel2.Visible;
        }
    }
}