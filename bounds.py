import math

class BoundingBox():

    def __init__(self, lat_min, lat_max, lon_min, lon_max):

        self.lat_min = lat_min
        self.lat_max = lat_max
        self.lon_min = lon_min
        self.lon_max = lon_max

    def get_min_point(self):

        return (self.lat_min, self.lon_min)

    def get_max_point(self):

        return (self.lat_max, self.lon_max)

class DividedBounds(BoundingBox):

    def __init__(self, divisions, *args):

        super().__init__(*args)
        self.divisions = divisions

    def boxes(self):

        divisor = int(math.sqrt(self.divisions))

        delta_lat = (self.lat_max - self.lat_min) / divisor
        delta_lon = (self.lon_max - self.lon_min) / divisor

        left_lon = self.lon_min
        bottom_lat = self.lat_min

        # Bottom to top
        for y in range(divisor):

            top_lat = bottom_lat + delta_lat

            # Left to right
            for x in range(divisor):

                right_lon = left_lon + delta_lon

                box = BoundingBox(bottom_lat, top_lat, left_lon, right_lon)
                yield box

                left_lon += delta_lon

            # Move up a row and reset
            bottom_lat += delta_lat
            left_lon = self.lon_min


if (__name__ == '__main__'):
    big_box = DividedBounds(0, 9, 0, 9, 9)

    for box in big_box.boxes():
        pass
