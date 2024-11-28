using Microsoft.AspNetCore.Mvc;
using QuadrilateralDistortion;
using System.Drawing;
using TrafficStopImageGeneratorWS;

namespace TrafficCameraWS.Controllers
{
    [ApiController]
    [Route("[controller]")]
    public class TrafficCameraWSController : ControllerBase
    {
        private readonly ILogger<TrafficCameraWSController> _logger;
        private static string INPUT_IMAGE_PATH = @"C:\BWHacker2023\images";
        private static object _imgLock = new object();

        public TrafficCameraWSController(ILogger<TrafficCameraWSController> logger)
        {
            _logger = logger;
        }

        [HttpGet]
        [Route("")]
        public string Ping()
        {
            return "TrafficCameraWS is working!";
        }

        [HttpPost]
        [Route("Capture")]
        public void Capture(TrafficDetail[] imageReq)
        {
            // Run the image generation in parallel.
            List<Task> taskList = new List<Task>();
            foreach (TrafficDetail trafficDetail in imageReq)
            {
                //CreateImageForTraffic(trafficDetail);
                taskList.Add(Task.Run(() => CreateImageForTraffic(trafficDetail)));
            }

            Task.WaitAll(taskList.ToArray());
        }

        [HttpPost]
        [Route("CaptureWithPerspective")]
        public void CaptureWithPerspective(TrafficDetail[] imageReq)
        {
            // Run the image generation in parallel.
            List<Task> taskList = new List<Task>();
            foreach (TrafficDetail trafficDetail in imageReq)
            {
                //CreateImageForTraffic(trafficDetail);
                taskList.Add(Task.Run(() => CreateImageForTrafficWithPerspective(trafficDetail)));
            }

            Task.WaitAll(taskList.ToArray());
        }

        private void CreateImageForTraffic(TrafficDetail trafficDetail)
        {
            // Open the empty road image that we'll draw on.
            string openRoadImgPath = Path.Combine(INPUT_IMAGE_PATH, "Oncoming Traffic - Empty - Camera Size - 800.png");
            Image emptyRoadImg2D = Bitmap.FromFile(openRoadImgPath);

            // Draw cars on the 2D road.
            Bitmap occupiedRoadImg2D = new Bitmap(emptyRoadImg2D.Width, emptyRoadImg2D.Height);

            using (Graphics g = Graphics.FromImage(occupiedRoadImg2D))
            {
                // Draw open road image on new image.
                g.DrawImage(emptyRoadImg2D, 0, 0);

                // Draw cars on new image.
                foreach (Car car in trafficDetail.carList)
                {
                    string carImgPath = Path.Combine(INPUT_IMAGE_PATH, "car" + car.carImageIdx.ToString("D2") + ".png");
                    Image carImg = (Bitmap)Bitmap.FromFile(carImgPath);

                    g.DrawImage(carImg, car.x1, car.y1, 20, 41);
                }
            }

            // Now make it 3D from the perspective of the intersection's camera.
            /*Bitmap flippedImage = new Bitmap((Image)occupiedRoadImg2D.Clone());
            flippedImage.RotateFlip(RotateFlipType.Rotate180FlipNone);

            Bitmap skewedImage = QuadDistort.Distort(flippedImage,
                                                     new Point(260, 0),
                                                     new Point(340, 0),
                                                     new Point(0, 450),
                                                     new Point(600, 450));


            using (Graphics g = Graphics.FromImage(skewedImage))
            {
                Color grassColor = Color.FromArgb(38, 127, 0);
                SolidBrush grassBrush = new SolidBrush(grassColor);

                // Create points that define polygon.
                Point point1 = new Point(0, 0);
                Point point2 = new Point(260, 0);
                Point point4 = new Point(0, 450);

                Point[] curvePoints = { point1, point2, point4 };
                g.FillPolygon(grassBrush, curvePoints);

                point1 = new Point(335, 0);
                point2 = new Point(600, 0);
                point4 = new Point(600, 460);

                Point[] curvePoints2 = { point1, point2, point4 };
                g.FillPolygon(grassBrush, curvePoints2);
                //stackBasedFloodFill(skewedImage, 0, 0, skewedImage.GetPixel(0, 0), Color.FromArgb(38, 127, 0));
            }

            // Save new image.
            if (System.IO.File.Exists(imageRequest.desiredOutputFilename))
            {
                System.IO.File.Delete(imageRequest.desiredOutputFilename);
            }*/

            /*if (System.IO.File.Exists(@"c:\work\test.png"))
            {
                System.IO.File.Delete(@"c:\work\test.png");
            }*/

            //Image occupiedRoadImg2DGrayslake = occupiedRoadImg2D
            occupiedRoadImg2D.Save(trafficDetail.desiredOutputFilename);
            //occupiedRoadImg2D.Save(@"c:\work\test.png");
            occupiedRoadImg2D.Dispose();

            return; // imageReq.desiredOutputFilename;
        }

        private void CreateImageForTrafficWithPerspective(TrafficDetail trafficDetail)
        {
            // Open the empty road image that we'll draw on.
            string openRoadImgPath = Path.Combine(INPUT_IMAGE_PATH, "Oncoming Traffic - Empty - Camera Size - 800.png");
            Image emptyRoadImg2D = Bitmap.FromFile(openRoadImgPath);

            // Draw cars on the 2D road.
            Bitmap occupiedRoadImg2D = new Bitmap(emptyRoadImg2D.Width, emptyRoadImg2D.Height);

            using (Graphics g = Graphics.FromImage(occupiedRoadImg2D))
            {
                // Draw open road image on new image.
                g.DrawImage(emptyRoadImg2D, 0, 0);

                // Draw cars on new image.
                foreach (Car car in trafficDetail.carList)
                {
                    string carImgPath = Path.Combine(INPUT_IMAGE_PATH, "car" + car.carImageIdx.ToString("D2") + ".png");
                    Image carImg = (Bitmap)Bitmap.FromFile(carImgPath);

                    g.DrawImage(carImg, car.x1, car.y1, 20, 41);
                }
            }

            // Now make it 3D from the perspective of the intersection's camera.
            Bitmap flippedImage = new Bitmap((Image)occupiedRoadImg2D.Clone());
            flippedImage.RotateFlip(RotateFlipType.Rotate180FlipNone);

            Bitmap skewedImage = QuadDistort.Distort(flippedImage,
                                                     new Point(260, 0),
                                                     new Point(340, 0),
                                                     new Point(0, 450),
                                                     new Point(600, 450));


            using (Graphics g = Graphics.FromImage(skewedImage))
            {
                Color grassColor = Color.FromArgb(38, 127, 0);
                SolidBrush grassBrush = new SolidBrush(grassColor);

                // Create points that define polygon.
                Point point1 = new Point(0, 0);
                Point point2 = new Point(260, 0);
                Point point4 = new Point(0, 450);

                Point[] curvePoints = { point1, point2, point4 };
                g.FillPolygon(grassBrush, curvePoints);

                point1 = new Point(335, 0);
                point2 = new Point(600, 0);
                point4 = new Point(600, 460);

                Point[] curvePoints2 = { point1, point2, point4 };
                g.FillPolygon(grassBrush, curvePoints2);
                //stackBasedFloodFill(skewedImage, 0, 0, skewedImage.GetPixel(0, 0), Color.FromArgb(38, 127, 0));
            }

            // Save new image.
            if (System.IO.File.Exists(trafficDetail.desiredOutputFilename))
            {
                System.IO.File.Delete(trafficDetail.desiredOutputFilename);
            }

            /*if (System.IO.File.Exists(@"c:\work\test.png"))
            {
                System.IO.File.Delete(@"c:\work\test.png");
            }*/

            //Image occupiedRoadImg2DGrayslake = occupiedRoadImg2D
            //occupiedRoadImg2D.Save(trafficDetail.desiredOutputFilename);
            //occupiedRoadImg2D.Dispose();

            skewedImage.Save(trafficDetail.desiredOutputFilename);
            skewedImage.Dispose();

            return; // imageReq.desiredOutputFilename;
        }
    }
}
