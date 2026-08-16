Data storage structure:

image_id   image_path           country     latitude   longitude   sequence_id   source
82371      raw/82371.jpg        France      48.851     2.351       abc123        Mapillary
82372      raw/82372.jpg        France      48.862     2.345       def456        Google Street View


image_id: UID for an individual picture
image_path: relative path from data/ directory to the stored image file
country: country where picture is from
latitude: latitude where picture is from (to 3 decimal places of precision)
longitude: longitude where picture is from (to 3 decimal places of precision)
sequence_id: UID for a capture group the image belonds to 
source: source where image came from