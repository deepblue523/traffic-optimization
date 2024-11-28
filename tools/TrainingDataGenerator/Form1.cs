using Accord.Video.FFMPEG;
using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Net;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Text.Json;
using System.Windows.Forms;

namespace TrafficVideoTrainingDataGenerator
{
    public partial class Form1 : Form
    {
        public class Car
        {
            public int carImageIdx;
            public int x1;
            public int y1;
            public int x2;
            public int y2;
            public double farWeight;
            public double nearWeight;
            public double middleWeight;
        }

        class Lane
        {
            public List<Car> carsInLane;

            public int firstCarPosition
            {
                get
                {
                    if (carsInLane.Count == 0)
                    {
                        return 0;
                    }
                    else 
                    {
                        return carsInLane[0].y1;
                    }
                }
            }

            public double totalFarWeight
            {
                get {
                    return carsInLane.Sum(oneCar => 
                                {
                                    return oneCar.farWeight;
                                });
                }
            }

            public double totalNearWeight
            {
                get
                {
                    return carsInLane.Sum(oneCar =>
                    {
                        return oneCar.nearWeight;
                    });
                }
            }

            public double totalMiddleWeight
            {
                get
                {
                    return carsInLane.Sum(oneCar =>
                    {
                        return oneCar.middleWeight;
                    });
                }
            }
        }

        class TrafficPattern
        {
            public Lane leftTurnLane;
            public Lane leftLane;
            public Lane rightLane;
            public List<Car> carsOnRoad_All;

            public bool leftTurnSensorTripped;

            public int firstCarPositionMainLanes
            {
                get
                {
                    if (leftLane.firstCarPosition == 0 && rightLane.firstCarPosition == 0)
                    {
                        return 0;
                    }
                    else if (leftLane.firstCarPosition == 0)
                    {
                        return rightLane.firstCarPosition;
                    }
                    else if (rightLane.firstCarPosition == 0)
                    {
                        return leftLane.firstCarPosition;
                    }
                    else
                    {
                        return Math.Min(leftLane.firstCarPosition, rightLane.firstCarPosition);
                    }
                }
            }

            public int firstCarPositionAllLanes
            {
                get
                {
                    if (leftTurnLane.firstCarPosition == 0 && this.firstCarPositionMainLanes == 0)
                    {
                        return 0;
                    }
                    else if (leftTurnLane.firstCarPosition == 0)
                    {
                        return this.firstCarPositionMainLanes;
                    }
                    else if (this.firstCarPositionMainLanes == 0)
                    {
                        return leftTurnLane.firstCarPosition;
                    }
                    else
                    {
                        return Math.Min(leftTurnLane.firstCarPosition, this.firstCarPositionMainLanes);
                    }
                }
            }

            public double totalFarWeight
            {
                get
                {
                    return carsOnRoad_All.Sum(x =>
                    { 
                        return x.farWeight;
                    });
                }
            }

            public double totalNearWeight
            {
                get
                {
                    return carsOnRoad_All.Sum(x =>
                    {
                        return x.nearWeight;
                    });
                }
            }

            public double totalMiddleWeight
            {
                get
                {
                    return carsOnRoad_All.Sum(x =>
                    {
                        return x.middleWeight;
                    });
                }
            }
        }

        class TrafficImageRequest
        {
            public string desiredOutputFilename { get; set; }
            public List<Car> carList { get; set; }
        }

        private Image _emptyRoadImg = null;
        private List<Image> _carImageList = new List<Image>();
        private List<Car> _carBoundingBoxes = new List<Car>();

        private int _lane1PosY;
        private int _lane2PosY;
        private int _lane3PosY;
        private int _lane4PosY;
        private int _positionOfStopLine = 22; // Pixel 22 is the position of the stop line in the image.
        private int _maxTrafficPatternsToGenerate = 20000; // Use multiples of 4 because the ML training uses batches of 4 (4 lights per intersection).

        private Random _rnd = new Random();

        private String _basePath = @"C:\BWHacker2023";

        [DllImport("gdi32.dll")]
        public static extern IntPtr SelectObject(IntPtr hdc, IntPtr hgdiobj);
        [DllImport("gdi32.dll")]
        public static extern IntPtr CreateSolidBrush(int crColor);
        [DllImport("gdi32.dll")]
        public static extern bool ExtFloodFill(IntPtr hdc, int nXStart, int nYStart,
            int crColor, uint fuFillType);
        [DllImport("gdi32.dll")]
        public static extern bool DeleteObject(IntPtr hObject);
        [DllImport("gdi32.dll")]
        public static extern int GetPixel(IntPtr hdc, int x, int y);
        public static uint FLOODFILLBORDER = 0;
        public static uint FLOODFILLSURFACE = 1;

        public static string IMAGE_GENERATION_WS_URL = "http://localhost:5065/";
        public static string TRAFFIC_IMG_OUTPUT_PATH = "C:\\BWHacker2023\\training_data\\";

        public Form1()
        {
            InitializeComponent();
        }

        private void goButton_Click(object sender, EventArgs e)
        {
            makeCarClones();
                
            // Set up a list where we will put our generated metadata correspond to each image.  The "id" column
            // correlates to an image # which is encoded in the dataset images' filenames.
            List<string> trafficMetadataList = new List<string>();
            trafficMetadataList.Add("id,image_filename,car_count,left_near,left_middle,left_far,right_near,right_middle,right_far,turn_near,turn_middle,turn_far,first_car_pos_left,first_car_pos_right,first_car_pos_turn");
            setMinCarDistance(22);

            textBox1.Text = "";
            textBox1.AppendText(trafficMetadataList[0]);

            // Clean out our target path.
            string[] filesToRemove = Directory.GetFiles($@"{_basePath}\training_data\", "*.png", SearchOption.AllDirectories);
            foreach (string filename in filesToRemove)
            {
                File.Delete(filename);
            }

            string videoOutFilename = @"C:\work\ImageDataGen.avi";
            if (File.Exists(videoOutFilename))
            {
                File.Delete(videoOutFilename);
            }

            VideoFileWriter writer = new VideoFileWriter();
            int width = this.Width % 2 == 1 ? this.Width = this.Width + 1 : this.Width;
            int height = this.Height % 2 == 1 ? this.Height = this.Height + 1 : this.Height;
            writer.Open(videoOutFilename, width, height, 20, VideoCodec.H264, 7000000);

            // We'll generate our sample traffic in a modified normal distribution.  The modification is that
            // the curve may be clipped if it goes past the intersection's stop line.
            for (int trafficPatternNumber = 0; trafficPatternNumber < _maxTrafficPatternsToGenerate; trafficPatternNumber++)
            {
                // Start with an empty road.
                //_emptyRoadImg = new Bitmap((Image)emptyRoadPictureBox.Image.Clone());

                //imageGenPictureBox.Image = _emptyRoadImg;
                _carBoundingBoxes.Clear();

                // Generate a traffic image with the given characteristics.
                TrafficPattern traffic = generateTrafficPattern(800); // _emptyRoadImg.Height);
                    

                // "Breathe" so we can see the image on the UI.
                Application.DoEvents();

                // Create our image.
                String relativeImageFilenameFar = $"image_{trafficPatternNumber}__" + 
                                                  $"LN{traffic.leftLane.totalNearWeight}_" +
                                                  $"LM{traffic.leftLane.totalMiddleWeight}_" +
                                                  $"LF{traffic.leftLane.totalFarWeight}___" +
                                                  $"RN{traffic.rightLane.totalNearWeight}_" +
                                                  $"RM{traffic.rightLane.totalMiddleWeight}_" +
                                                  $"RF{traffic.rightLane.totalFarWeight}___" +
                                                  $"TN{traffic.leftTurnLane.totalNearWeight}_" +
                                                  $"TM{traffic.leftTurnLane.totalMiddleWeight}_" +
                                                  $"TF{traffic.leftTurnLane.totalFarWeight}___" +
                                                  $"DL{traffic.leftLane.firstCarPosition}_" +
                                                  $"DR{traffic.rightLane.firstCarPosition}_" +
                                                  $"DT{traffic.leftTurnLane.firstCarPosition}" +
                                                  ".png";
                
                String imageFilenameFar = Path.Combine(TRAFFIC_IMG_OUTPUT_PATH + @"images\", relativeImageFilenameFar);
                imageFilenameFar = Path.GetFullPath(imageFilenameFar);

                TrafficImageRequest trafficImageRequest = new TrafficImageRequest();
                trafficImageRequest.desiredOutputFilename = imageFilenameFar;
                trafficImageRequest.carList = traffic.carsOnRoad_All;
                TrafficImageRequest[] trafficImageRequestWrapper = { trafficImageRequest };

                // Generate request to draw the image to the given file!!!
                var options = new JsonSerializerOptions { WriteIndented = true, IncludeFields = true };
                string trafficImageRequestSerialized = JsonSerializer.Serialize(trafficImageRequestWrapper, options);

                //Console.WriteLine("===============================================================================================================");
                //Console.WriteLine(trafficImageRequestSerialized);

                using (WebClient wc = new WebClient())
                {
                    wc.BaseAddress = IMAGE_GENERATION_WS_URL;
                    wc.Headers[HttpRequestHeader.ContentType] = "application/json";
                    //wc.UploadString("TrafficCameraWS/CaptureWithPerspective", "POST", trafficImageRequestSerialized);
                    wc.UploadString("TrafficCameraWS/Capture", "POST", trafficImageRequestSerialized);
                }

                // Update UI and training data accumulator.
                Image genImage = Bitmap.FromFile(imageFilenameFar);
                pictureBox1.Image = genImage;

                string metadataLine = $"{trafficPatternNumber},\"{relativeImageFilenameFar}\",{traffic.carsOnRoad_All.Count},{traffic.leftLane.totalNearWeight},{traffic.leftLane.totalMiddleWeight},{traffic.leftLane.totalFarWeight},{traffic.rightLane.totalNearWeight},{traffic.rightLane.totalMiddleWeight},{traffic.rightLane.totalFarWeight},{traffic.leftTurnLane.totalNearWeight},{traffic.leftTurnLane.totalMiddleWeight},{traffic.leftTurnLane.totalFarWeight},{traffic.leftLane.firstCarPosition},{traffic.rightLane.firstCarPosition},{traffic.leftTurnLane.firstCarPosition}";
                trafficMetadataList.Add(metadataLine);

                string metadataLineUi = metadataLine.Substring(metadataLine.IndexOf(',', 10) + 1); // Past first comma.

                textBox1.AppendText($"\n{relativeImageFilenameFar}");
                textBox2.AppendText($"\n{metadataLineUi}");

                using (var bmp = new Bitmap(this.Width, this.Height))
                {
                    this.DrawToBitmap(bmp, new Rectangle(0, 0, bmp.Width, bmp.Height));
                    writer.WriteVideoFrame(bmp);
                }
            }

            File.WriteAllLines($@"{_basePath}\training_data\traffic_metadata.csv", trafficMetadataList);

            // Cleanup;
            cleanupImages();
            writer.Close();
        }

        private double calculatePercentOverlap(Rectangle rect1, Rectangle rect2)
        {
            if (!rect1.IntersectsWith(rect2))
            {
                return 0;
            }

            Rectangle inter = rect1;
            inter.Intersect(rect2);
    
              return (double) (inter.Width * inter.Height) * 2.0 /
                (double) (rect1.Width * rect1.Height + 
                         rect2.Width * rect2.Height);
        }

    private TrafficPattern generateTrafficPattern(int roadLength)
        {
            TrafficPattern trafficPattern = new TrafficPattern();
            trafficPattern.leftTurnLane = new Lane();
            trafficPattern.leftLane = new Lane();
            trafficPattern.rightLane = new Lane();
            trafficPattern.leftTurnLane.carsInLane = new List<Car>();
            trafficPattern.leftLane.carsInLane = new List<Car>();
            trafficPattern.rightLane.carsInLane = new List<Car>();
            trafficPattern.carsOnRoad_All = new List<Car>();

            // Insert empty samples occasionally.
            if (_rnd.NextDouble() < 0.0001)
            {
                return trafficPattern;
            }
            
            // Left turn lane.
            if (_rnd.NextDouble() < 0.75)
            {
                trafficPattern.leftTurnLane.carsInLane.AddRange(generateTrafficPatternForLane2(
                                    _positionOfStopLine,
                                    55,
                                    roadLength,
                                    roadLength, //600,
                                    0.0000001,
                                    0.0,
                                    (int)((double)_rnd.NextDouble() * 100),
                                    1.1));

                trafficPattern.leftTurnSensorTripped = trafficPattern.leftTurnLane.carsInLane.Count > 0
                                                           ? trafficPattern.leftTurnLane.carsInLane[0].y1 < (_positionOfStopLine + 50)
                                                           : false;
            }

            // Left lane.
            double minCarLikelihoodLow = _rnd.NextDouble() * 0.005;
            double maxCarLikelihoodHigh = minCarLikelihoodLow * 2; // Math.Max(minCarLikelihoodLow, _rnd.NextDouble() * 0.005);

            if (_rnd.NextDouble() < 0.9)
            {
                trafficPattern.leftLane.carsInLane.AddRange(generateTrafficPatternForLane2(
                                _positionOfStopLine + (int)_rnd.NextDouble() * roadLength,
                                77,
                                roadLength,
                                roadLength,
                                minCarLikelihoodLow,
                                maxCarLikelihoodHigh,
                                (int)((double)_rnd.NextDouble() * roadLength),
                                1.0));
            }

            // Right lane.
            if (_rnd.NextDouble() < 0.9)
            {
                trafficPattern.rightLane.carsInLane.AddRange(generateTrafficPatternForLane2(
                                _positionOfStopLine + (int)_rnd.NextDouble() * roadLength,
                                100,
                                roadLength,
                                roadLength,
                                minCarLikelihoodLow,
                                maxCarLikelihoodHigh,
                                (int)((double)_rnd.NextDouble() * roadLength),
                                1.0));
            }

            trafficPattern.carsOnRoad_All.AddRange(trafficPattern.leftTurnLane.carsInLane);
            trafficPattern.carsOnRoad_All.AddRange(trafficPattern.leftLane.carsInLane);
            trafficPattern.carsOnRoad_All.AddRange(trafficPattern.rightLane.carsInLane);

            return trafficPattern;
        }

        private void makeCarClones()
        {
            _carImageList.Clear();

            _carImageList.Add((Image)pictureBox2.Image.Clone());
            _carImageList.Add((Image)pictureBox3.Image.Clone());
            _carImageList.Add((Image)pictureBox4.Image.Clone());
            _carImageList.Add((Image)pictureBox5.Image.Clone());
            _carImageList.Add((Image)pictureBox6.Image.Clone());
            _carImageList.Add((Image)pictureBox7.Image.Clone());
            _carImageList.Add((Image)pictureBox8.Image.Clone());
            _carImageList.Add((Image)pictureBox9.Image.Clone());
            _carImageList.Add((Image)pictureBox10.Image.Clone());
            _carImageList.Add((Image)pictureBox11.Image.Clone());
            _carImageList.Add((Image)pictureBox12.Image.Clone());
            _carImageList.Add((Image)pictureBox13.Image.Clone());
        }

        private void cleanupImages()
        { 
            foreach (Image img in _carImageList)
            {
                img.Dispose();
            }

            _carImageList.Clear();

            //imageGenPictureBox.Image = null;
            //_emptyRoadImg.Dispose();
            //_emptyRoadImg = null;
        }

        private void setMinCarDistance(int minCarDistance)
        {
            _lane1PosY = minCarDistance;
            _lane2PosY = minCarDistance;
            _lane3PosY = minCarDistance;
            _lane4PosY = minCarDistance;
        }

        private List<Car> generateTrafficPatternForLane(
                                int positionOfStopLine,
                                int xPos,
                                int roadLength,
                                int stopGenPos,
                                double carProbabilityBegin,
                                double carProbabilityEnd,
                                int startingScanYPos,
                                double frustratrationAdjFactor)  // Use for left turn lane, which is quite annoying for many people.
        {
            List<Car> resultSet = new List<Car>();

            // Start generating!
            int totalUsableRoadLength = (roadLength - positionOfStopLine);

            double frustrationBase = 0.50;
            double frustration = frustrationBase;
            double frustrationStep = frustrationBase / (roadLength - positionOfStopLine);
            int laneScanYPos = 22;

            while (laneScanYPos < stopGenPos)
            {
                if (laneScanYPos < startingScanYPos)
                {
                    laneScanYPos++;
                    continue;
                }
                
                double positionCarPct = (double)(laneScanYPos - positionOfStopLine) / totalUsableRoadLength;
                double carProbability = (double)carProbabilityBegin + (carProbabilityEnd - carProbabilityBegin) * positionCarPct;

                bool laneHasCar = _rnd.NextDouble() < Math.Abs(carProbability);

                // Left turn lane.
                if (laneHasCar)
                {
                    Car car = new Car();

                    int carImageIdx = _rnd.Next(12); // 0-based.
                    car.carImageIdx = carImageIdx + 1; // a-base.

                    car.x1 = xPos;
                    car.y1 = laneScanYPos;
                    car.x2 = car.x1 + _carImageList[carImageIdx].Width;
                    car.y2 = car.y1 + _carImageList[carImageIdx].Height;

                    // Compute frustration factor for this car.
                    car.nearWeight = frustration;
                    car.farWeight = frustrationBase - frustration;
                    car.middleWeight = frustrationBase - (frustration / 2);

                    resultSet.Add(car);

                    laneScanYPos += 41 /* car.image.Height */ + 5;
                }
                else
                {
                    laneScanYPos += 1;
                }

                frustration += frustrationStep;
            }

            return resultSet;
        }

        private List<Car> generateTrafficPatternForLane2(
                                int positionOfStopLine,
                                int xPos,
                                int roadLength,
                                int stopGenPos,
                                double carProbabilityBegin,
                                double carProbabilityEnd,
                                int startingScanYPos,
                                double frustratrationAdjFactor)  // Use for left turn lane, which is quite annoying for many people.
        {
            List<Car> resultSet = new List<Car>();
            int totalUsableRoadLength = (roadLength - positionOfStopLine);

            // Start generating!
            int laneScanYPos = positionOfStopLine;
            double carProbabilityInc = carProbabilityBegin / 800;
            double factor = 0.5 + _rnd.NextDouble();

            while (laneScanYPos < 800)
            {
                //double carProbabilityCurrentPos = (carProbabilityInc * laneScanYPos) * _rnd.NextDouble();
                //bool laneHasCar = (carProbabilityCurrentPos <= carProbabilityBegin) && (carProbabilityCurrentPos >= carProbabilityEnd);

                bool laneHasCar = (_rnd.NextDouble() * factor) < 0.0075;

                if (laneHasCar)
                {
                    Car car = new Car();

                    int carImageIdx = _rnd.Next(12); // 0-based.
                    car.carImageIdx = carImageIdx + 1; // 1-based.

                    car.x1 = xPos;
                    car.y1 = laneScanYPos;
                    car.x2 = car.x1 + _carImageList[carImageIdx].Width;
                    car.y2 = car.y1 + _carImageList[carImageIdx].Height;

                    // Compute frustration factor for this car.
                    double scanPosPctFromNear = (double) laneScanYPos / 800;

                    if (laneScanYPos < 200) 
                    {
                        car.nearWeight = 1;
                        car.middleWeight = 0;
                        car.farWeight = 0;
                    }
                    else if (laneScanYPos < 400)
                    {
                        car.nearWeight = 0;
                        car.middleWeight = 1;
                        car.farWeight = 0;
                    }
                    else
                    {
                        car.nearWeight = 0;
                        car.middleWeight = 0;
                        car.farWeight = 1;
                    }

                    resultSet.Add(car);

                    laneScanYPos += 41 /* car.image.Height */ + 5;
                }
                else
                {
                    laneScanYPos += 1;
                }
            }

            return resultSet;
        }

        private bool getRandomBool(double threshhold = 0.5)
        {
            return _rnd.NextDouble() >= threshhold;
        }

        private void imageGenPictureBox_Click(object sender, EventArgs e)
        {

        }
        private void floodFill(Image img, int x, int y, Color targetColor, Color replacementColor)
        {
            Rectangle rect = new Rectangle(0, 0, img.Width - 1, img.Height - 1);
            Pen pen = new Pen(replacementColor);

            using (Graphics vGraphics = Graphics.FromImage(img))
            {
                //vGraphics.DrawRectangle(pen, new Rectangle((int) rect.X, (int)rect.Y, (int)rect.Right, (int)rect.Bottom));
                vGraphics.DrawRectangle(pen, new Rectangle((int)rect.X, (int)rect.Y, (int)rect.Right, (int)rect.Bottom));

                /*IntPtr vDC = vGraphics.GetHdc();
                IntPtr vBrush = CreateSolidBrush(ColorTranslator.ToWin32(fillColor));
                IntPtr vPreviouseBrush = SelectObject(vDC, vBrush);

                ExtFloodFill(vDC, x, x, GetPixel(vDC, x, x), FLOODFILLSURFACE);
                SelectObject(vDC, vPreviouseBrush);
                DeleteObject(vBrush);
                vGraphics.ReleaseHdc(vDC);*/
            }
        }

        private void stackBasedFloodFill(Bitmap bmp, int x, int y, Color targetColor, Color replacementColor)
        {
            Point pt = new Point(x, y);
            Stack<Point> pixels = new Stack<Point>();
            targetColor = bmp.GetPixel(pt.X, pt.Y);
            pixels.Push(pt);

            while (pixels.Count > 0)
            {
                Point a = pixels.Pop();
                if (a.X < bmp.Width && a.X > 0 &&
                        a.Y < bmp.Height && a.Y > 0)//make sure we stay within bounds
                {

                    if (bmp.GetPixel(a.X, a.Y) == targetColor)
                    {
                        bmp.SetPixel(a.X, a.Y, replacementColor);
                        pixels.Push(new Point(a.X - 1, a.Y));
                        pixels.Push(new Point(a.X + 1, a.Y));
                        pixels.Push(new Point(a.X, a.Y - 1));
                        pixels.Push(new Point(a.X, a.Y + 1));
                    }
                }
            }
            //pictureBox1.Refresh(); //refresh our main picture box
            return;
        }
    }
}
