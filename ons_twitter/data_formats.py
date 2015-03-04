"""
Description:    Supplementary Python file, containing file formats for Twitter -> MongoDB imports/exports.
Author:         Bence Komarniczky
Date:           02/March/2015
Python version: 3.4
"""

from datetime import datetime
from osgeo import ogr, osr
from bson.son import SON


class Tweet():
    """
    Tweet class that contains a JSON object of tweet information.
    """

    def __init__(self, data=None, method=None):
        """
        Initialise class. Both data and method variables can be left empty for later completion of Tweet object.

        :param data:    Information to initialise the Tweet. Can be a list of variables (csv input) or a dictionary from
                        from Twitter API input.
        :param method:  Can hold 3 values: None, "csv", "json". None sets up empty Tweet object with NAs, csv expects
                        data to be a list, while json expects data to be dictionary from Twitter API/GNIP.
        :return:        Twitter object. Check .get_error() to see any errors.
        """
        self.error_number = 0
        self.error_description = []

        empty_dictionary = {'_id': [],
                            'user_id': "NA",
                            'unix_time': "NA",
                            'time': {
                                "timestamp": "NA",
                                "date": "NA",
                                "tod": "NA",
                                "dow": "NA",
                                "month": "NA"},
                            'tweet': {
                                "user_name": "NA",
                                "text": "NA",
                                "location": "NA",
                                "place": "NA",
                                "language": "NA",
                                "country": "NA",
                                "lat_long": ("NA", "NA"),
                                "coordinates": ("NA", "NA"),
                                "distance_from_centroid": "NA",
                                "address": {
                                    "UPRN": "NA",
                                    "coordinates": ["NA", "NA"],
                                    "postcode": "NA",
                                    "levels": {'oa11': "NA",
                                               'msoa11': "NA",
                                               'lsoa11': "NA",
                                               'oslaua': "NA",
                                               'osward': "NA"},
                                    "classification": {
                                        "full": "NA",
                                        "abbreviated": "NA"},
                                    "distance": "NA"}}}

        if method is None:
            self.dictionary = empty_dictionary

        elif method == "csv":
            self.dictionary = empty_dictionary

            # check if last column is anything other than empty (generated by csv reader)
            # if not empty, then re-format the data using the parse_wrong_data function (there will be an extra comma)
            if (len(data[-1]) > 0) and (len(data) > 10):
                data = parse_wrong_data(data, debug=False)

            # modify csv structure here, expecting input of 11 columns
            try:
                self.dictionary["user_id"] = int(float(data[1]))
                self.dictionary["unix_time"] = int(float(data[0]))
                self.dictionary["tweet"]["user_name"] = data[2]
                self.dictionary["tweet"]["language"] = data[3]
                self.dictionary["tweet"]["location"] = data[4]
                self.dictionary["tweet"]["place"] = data[5]
                self.dictionary["tweet"]["country"] = data[6]
                self.dictionary["tweet"]["text"] = data[9]
            except ValueError:
                self.error_number = 2
                self.error_description.append("Invalid data supplied:    " + ",".join(data))

            # handle missing coordinates
            try:
                self.dictionary["tweet"]["lat_long"] = (float(data[7]), float(data[8]))
                self.dictionary["tweet"]["coordinates"] = lat_long_to_osgb(
                    self.dictionary["tweet"]["lat_long"])
            except ValueError:
                self.dictionary["tweet"]["lat_long"] = ("NA", "NA")
                self.dictionary["tweet"]["coordinates"] = ("NA", "NA")
                self.error_number = 1
                self.error_description.append("Invalid lat_long coordinates supplied:    " + ",".join(data))

            # add time variables
            self.generate_time_input()

        elif method == "json":
            pass
        else:
            print("Invalid method supplied to Tweet class!")

    def get_errors(self, print_status=False):
        """
        Method for checking error status of Tweet object.

        :param print_status:
        :return: Integer: 0 = "No errors", 1 = "no geo-location", 2 = "Any other error"
        """

        if print_status:
            print(self.error_description)
        return self.error_number

    def get_info(self):
        """
        Method for pretty printing tweets.
        """

        from pprint import pprint
        pprint(self.dictionary)

    def generate_time_input(self):
        """"
        Method for converting raw unix_time input into different time variables.
        These new variables are then inserted into the tweet object. Used during initialisation.
        """

        # dependent input
        self.dictionary["_id"] = (self.dictionary["user_id"],
                                  self.dictionary["unix_time"])

        # time conversions | dependent input

        # timestamp
        self.dictionary["time"]["timestamp"] = datetime.fromtimestamp(
            self.dictionary["unix_time"]).strftime("%Y-%m-%d %X")
        # date
        self.dictionary["time"]["date"] = datetime.fromtimestamp(
            self.dictionary["unix_time"]).strftime("%Y-%m-%d")
        # month, abbreviated, e.g: Jan, Feb ...
        self.dictionary["time"]["month"] = datetime.fromtimestamp(
            self.dictionary["unix_time"]).strftime("%b")
        # Time of day hh:mm:ss
        self.dictionary["time"]["tod"] = datetime.fromtimestamp(
            self.dictionary["unix_time"]).strftime("%X")
        # Day of week Mon, Tue ...
        self.dictionary["time"]["dow"] = datetime.fromtimestamp(
            self.dictionary["unix_time"]).strftime("%a")

    def find_tweet_address(self, mongo_connection):
        """
        Finds the closest address point to the tweet from geo-indexed mongodb address base.
        :param mongo_connection: Geo-index mongodb collection.
        :return: 1 if address is found, 0 if no address is found within 300m of tweet.
        """
        # construct query
        query = {"coordinates": SON([("$near", self.dictionary["tweet"]["coordinates"]),
                                     ("$maxDistance", 300)])}
        # ask for single closest address if any
        closest_address_list = tuple(mongo_connection.find(query, {"_id": 0}).limit(1))

        # check if it has found any
        if len(closest_address_list) == 0:
            # if there are no address within 300m then add error description
            self.error_description.append("No address found within 300 meters")
            # add NA as distance
            self.dictionary["tweet"]["address"]["distance"] = "NA"
            return 1
        else:
            # add address
            self.dictionary["tweet"]["address"] = closest_address_list[0]
            # add distance (rounded to 3 decimal places
            self.dictionary["tweet"]["address"]["distance"] = distance(
                self.dictionary["tweet"]["coordinates"],
                closest_address_list[0]["coordinates"])
            return 0

    def add_cluster_info(self, cluster_data):
        pass

    def get_country_code(self):
        """
        Return the country code from the tweet. If non-GB then handle as special.
        """
        return self.dictionary["tweet"]["country"]


def lat_long_to_osgb(lat_long):
    """
    Convert latitude, longitude coordinates to UK easting, northing coordinates.

    :param lat_long: List or tuple of latitude, longitude coordinates.
    :return: List of easting (X), northing (Y) coordinates.
    """
    lat = lat_long[0]
    lng = lat_long[1]
    # Source is WSG84 (lat, lng) i.e. EPSG 4326:
    source = osr.SpatialReference()
    source.ImportFromEPSG(4326)
    # Target is osgb i.e. EPSG 27700:
    target = osr.SpatialReference()
    target.ImportFromEPSG(27700)
    # Prepare transformer
    transform = osr.CoordinateTransformation(source, target)

    # Create source point - coords are X, Y i.e. lng, lat:
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(lng, lat)
    # Now transform it to target coord system:
    point.Transform(transform)

    # Return point as an (X, Y) tuple i.e. (easting, northing):
    return [int(point.GetX()), int(point.GetY())]


def parse_wrong_data(data, debug=False):
    """
    Used for parsing incorrect csv data formats into correct list objects.
    Some tweets contain "," in the place description or user name. This can cause the raw input list to be too long.
    If the last object contains the tweet information and the list is longer then expected, then this function
    will find the extra element and remove it from the list.
    A new, cleaned data is returned.
    Main goal is to keep Longitude/Latitude information intact.
    :param data:    list resulting from csv reader - one row. User should check whether last element is non-empty. This
                    indicates invalid row.
    :param debug:   boolean for printing debugging information
    :return:        cleaned data as as list of correct length (not guaranteed)
    """

    if debug:
        print("\nInput:", data)
    # country code should be in 6th place, everything after it should be computer generated
    # separate data into 3 objects - before/new/after. New_data will contain problematic sections of input
    country_index = data.index("GB")
    before_new_data = data[:2]
    new_data = data[2:(country_index - 1)]
    after_new_data = data[(country_index - 1):]
    # convert to string
    string_data = ",".join(new_data)

    # read json document
    from json import load as jload
    language_codes_json = jload(open("twitter_lang_codes.JSON"))
    language_codes = []
    for one_item in language_codes_json:
        language_codes.append(one_item["code"])

    # loop over all language codes from Twitter
    for language in language_codes:
        lang_index = string_data.find(language)
        # if language code is found
        if lang_index != -1:
            if debug:
                print(language, lang_index)

            # separate at language code
            first_half = string_data[0:lang_index].split(sep=",")
            second_half = string_data[lang_index:].split(sep=",")

            # reduce both list to their correct length
            while len(first_half) > 1:
                first_half.pop()
            while len(second_half) > 2:
                second_half.pop()

            if debug:
                print(first_half)
                print(second_half)

            # paste new_data back together and finish loop
            new_data = first_half + second_half
            break

    # put data back together
    data = before_new_data + new_data + after_new_data

    if debug:
        print("\n Final output:\n", data, "\n")
    return data


def distance(point1, point2):
    """
    Given two tuples or lists, returns the distance between the two points, rounded to 3 decimal places.
    :param point1: First point of coordinates. (Tuple/list)
    :param point2: Second point of coordinates. (Tuple/list)
    :return: float
    """

    euclidean_squared = ((point1[0] - point2[0]) ** 2) + ((point1[1] - point2[1]) ** 2)
    return round(euclidean_squared ** 0.5, 3)