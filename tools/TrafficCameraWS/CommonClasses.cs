namespace TrafficStopImageGeneratorWS
{
    public class Car
    {
        public int carImageIdx { get; set; }
        public int x1 { get; set; }
        public int y1 { get; set; }
        public int x2 { get; set; }
        public int y2 { get; set; }
    }

    public class TrafficDetail
    {
        public string desiredOutputFilename { get; set; }
        public List<Car> carList { get; set; }
    }

    public class TrafficImageRequest
    {
        public string bawk;
        //public List<TrafficDetail> trafficDetailSet;
    }
}