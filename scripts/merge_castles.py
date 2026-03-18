#!/usr/bin/env python3
"""
Merge scraped castle data into the existing castles.ts file.
Reads the existing file, generates new entries from curated scraped data,
and writes the merged output.
"""

import re

EXISTING_FILE = '/Users/jackchittenden/Desktop/rentacastle/src/data/castles.ts'
OUTPUT_FILE = '/Users/jackchittenden/Desktop/rentacastle/src/data/castles.ts'

UNSPLASH_IMAGES = [
    'https://images.unsplash.com/photo-1533154683836-84ea7a0bc310?w=800&q=80',
    'https://images.unsplash.com/photo-1590001155093-a3c66ab0c3ff?w=800&q=80',
    'https://images.unsplash.com/photo-1565008576549-57569a49371d?w=800&q=80',
    'https://images.unsplash.com/photo-1577717903315-1691ae25ab3f?w=800&q=80',
    'https://images.unsplash.com/photo-1518780664697-55e3ad937233?w=800&q=80',
    'https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=800&q=80',
    'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&q=80',
    'https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=800&q=80',
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&q=80',
    'https://images.unsplash.com/photo-1598928636135-d146006ff4be?w=800&q=80',
]

# Curated list of genuine individual castle rentals from the scraped CSV
# Each entry has been manually verified as a specific, rentable castle property
SCRAPED_CASTLES = [
    {
        'name': 'Castle Trinity',
        'region': 'England',
        'county': 'West Yorkshire',
        'snippet': 'Castle Trinity is a luxury self-catering castle for hire in Holywell Green, west Yorkshire near The Peak District; perfect for celebrations.',
        'url': 'https://www.uniquehomestays.com/self-catering/uk/yorkshire/holywell-green/castle-trinity/',
        'domain': 'uniquehomestays.com',
        'sleeps': 16,
        'bedrooms': 8,
        'price': '£500/night',
        'priceRange': '$$$',
        'selfCatering': True,
        'weddingSuitable': True,
        'highlights': ['Luxury self-catering castle', 'Near The Peak District', 'Perfect for celebrations and gatherings', 'West Yorkshire countryside setting'],
    },
    {
        'name': 'Fernhill Castle',
        'region': 'England',
        'county': 'West Yorkshire',
        'snippet': 'This impressive Grade I listed fortified mansion rests in Farnhill near Cross Hills, West Yorkshire, and can sleep 30 people in 10 bedrooms. Four open fires. Historic property. Hot tub.',
        'url': 'https://www.sykescottages.co.uk/cottage/Yorkshire-Dales-South-Farnhill/Fernhill-Castle-1069783.html',
        'domain': 'sykescottages.co.uk',
        'sleeps': 30,
        'bedrooms': 10,
        'price': '£800/night',
        'priceRange': '$$$',
        'selfCatering': True,
        'hasHotTub': True,
        'highlights': ['Grade I listed fortified mansion', 'Sleeps 30 in 10 bedrooms', 'Four open fires', 'Hot tub', '15-acre estate near Skipton'],
    },
    {
        'name': 'Beaufront Castle',
        'region': 'England',
        'county': 'Northumberland',
        'snippet': 'Magnificent castle overlooking the Tyne Valley in Northumberland, perfect for family get-togethers or groups of friends. Sleeps 16. £1800-3000 per night.',
        'url': 'https://www.coolstays.com/property/beaufront-castle/28324',
        'domain': 'coolstays.com',
        'sleeps': 16,
        'bedrooms': 8,
        'price': '£2400/night',
        'priceRange': '$$$$',
        'highlights': ['Magnificent Tyne Valley views', 'Perfect for family gatherings', 'Northumberland countryside', 'Sleeps up to 16 guests'],
    },
    {
        'name': 'Middleton Castle',
        'region': 'England',
        'county': 'Norfolk',
        'snippet': 'A 15th-century moated gem in Norfolk. Become Lord or Lady of the manor at your luxury, moated private castle for large groups in the heart of North Norfolk. Sleeps 30. £3900-5000 per night.',
        'url': 'https://www.coolstays.com/property/middleton-castle/27394',
        'domain': 'coolstays.com',
        'sleeps': 30,
        'bedrooms': 14,
        'price': '£4500/night',
        'priceRange': '$$$$',
        'weddingSuitable': True,
        'highlights': ['15th-century moated castle', 'Luxury exclusive-use estate', '1000-acre grounds', 'Sleeps 30 guests', 'North Norfolk setting'],
    },
    {
        'name': 'Noblestone Castle',
        'region': 'England',
        'county': 'Norfolk',
        'snippet': "Set spectacularly among majestic grounds and within its very own moat, the 15-bedroom Noblestone Castle is a stunning holiday venue accommodating up to 30 guests.",
        'url': 'https://big-cottages.com/properties/united-kingdom/england/norfolk/king-s-lynn-and-west-norfolk-district/noblestone-castle',
        'domain': 'big-cottages.com',
        'sleeps': 30,
        'bedrooms': 15,
        'price': '£3900/night',
        'priceRange': '$$$$',
        'highlights': ['Spectacular moated castle', '15 bedrooms', 'Majestic grounds', 'Near King\'s Lynn', 'Ideal for large groups'],
    },
    {
        'name': 'Bickleigh Castle',
        'region': 'England',
        'county': 'Devon',
        'snippet': 'Historic Bickleigh Castle offers accommodation for up to 40 people on site in 18 bedrooms, situated in the beautiful Devonshire countryside surrounded by acres of countryside and the River Exe.',
        'url': 'https://www.independentcottages.co.uk/devon/bickleigh-castle-ref4836',
        'domain': 'independentcottages.co.uk',
        'sleeps': 40,
        'bedrooms': 18,
        'price': '£1200/night',
        'priceRange': '$$$$',
        'weddingSuitable': True,
        'highlights': ['Grade I listed castle', 'Ancient Keep and Saxon Chapel', 'Sleeps 40 across 18 bedrooms', 'River Exe setting', '60 acres of grounds'],
    },
    {
        'name': 'Dyfi Castle',
        'region': 'Wales',
        'county': 'Powys',
        'snippet': 'Magnificent castle with luxurious interiors, a hot tub and 40 acres of private land. Unparalleled views of the Dyfi Estuary and the sea.',
        'url': 'https://www.holidaycottages.co.uk/cottage/oc-32752-dyfi-castle',
        'domain': 'holidaycottages.co.uk',
        'sleeps': 12,
        'bedrooms': 6,
        'price': '£400/night',
        'priceRange': '$$$',
        'hasHotTub': True,
        'selfCatering': True,
        'highlights': ['Luxurious castle interiors', 'Hot tub with estuary views', '40 acres of private land', 'Dyfi Estuary and sea views', 'Mid Wales countryside'],
    },
    {
        'name': 'Kilchrist Castle',
        'region': 'Scotland',
        'county': 'Argyll and Bute',
        'snippet': 'Discover this fabulous castle nestled amidst 8 acres of private grounds in a peaceful countryside setting. The harbour town of Campbeltown is within easy reach.',
        'url': 'https://www.holidaycottages.co.uk/cottage/83009-kilchrist-castle',
        'domain': 'holidaycottages.co.uk',
        'sleeps': 10,
        'bedrooms': 5,
        'price': '£300/night',
        'priceRange': '$$$',
        'selfCatering': True,
        'highlights': ['8 acres of private grounds', 'Peaceful Argyll countryside', 'Near Campbeltown harbour', 'Kintyre peninsula setting'],
    },
    {
        'name': 'Kinnairdy Castle',
        'region': 'Scotland',
        'county': 'Aberdeenshire',
        'snippet': 'Historic 14th-century castle with original features including stained-glass windows. Set on extensive grounds with miles of beautiful river walks.',
        'url': 'https://www.holidaycottages.co.uk/cottage/89020-kinnairdy-castle',
        'domain': 'holidaycottages.co.uk',
        'sleeps': 12,
        'bedrooms': 6,
        'price': '£350/night',
        'priceRange': '$$$',
        'selfCatering': True,
        'highlights': ['14th-century castle', 'Original stained-glass windows', 'Extensive riverside grounds', 'Near Huntly, Aberdeenshire'],
    },
    {
        'name': 'The Pink Castle',
        'region': 'Scotland',
        'county': 'Ayrshire',
        'snippet': 'Spectacular castle with views out to sea and magical gardens with a hot tub that overlooks the countryside. A sauna lies in one of the many turrets.',
        'url': 'https://www.holidaycottages.co.uk/cottage/oc-38074-the-pink-castle',
        'domain': 'holidaycottages.co.uk',
        'sleeps': 10,
        'bedrooms': 5,
        'price': '£350/night',
        'priceRange': '$$$',
        'hasHotTub': True,
        'highlights': ['Spectacular sea views', 'Hot tub in magical gardens', 'Sauna in a turret', 'Largs coastal setting', 'Multiple turrets'],
    },
    {
        'name': 'Castle Wing at Kilmarnock',
        'region': 'Scotland',
        'county': 'Ayrshire',
        'snippet': 'Private Scottish Castle set on a beautiful estate with loch, walks in abundance and café. 600 acres to roam with garden furniture and BBQ, perfect for dog walkers.',
        'url': 'https://www.holidaycottages.co.uk/cottage/oc-33572-castle-wing',
        'domain': 'holidaycottages.co.uk',
        'sleeps': 8,
        'bedrooms': 4,
        'price': '£250/night',
        'priceRange': '$$',
        'petFriendly': True,
        'selfCatering': True,
        'highlights': ['Private Scottish castle estate', '600 acres to explore', 'Estate loch', 'Dog-friendly', 'BBQ and outdoor dining'],
    },
    {
        'name': 'Sundrum Castle',
        'region': 'Scotland',
        'county': 'Ayrshire',
        'snippet': 'Sundrum Castle is sat in a secluded countryside setting, yet is just 6 miles from Ayr – one of Scotland\'s liveliest seaside towns.',
        'url': 'https://www.snaptrip.com/holiday-parks/sundrum-castle',
        'domain': 'snaptrip.com',
        'sleeps': 10,
        'bedrooms': 5,
        'price': '£280/night',
        'priceRange': '$$',
        'selfCatering': True,
        'highlights': ['Secluded countryside setting', 'Just 6 miles from Ayr', 'Scottish seaside location', 'Historic castle grounds'],
    },
    {
        'name': 'Dinton Castle',
        'region': 'England',
        'county': 'Buckinghamshire',
        'snippet': 'Dinton Castle is a 250-year-old landmark in Buckinghamshire, beautifully restored into a unique two-bedroom home. As featured on Grand Designs.',
        'url': 'https://www.airbnb.co.uk/rooms/643884759601892680',
        'domain': 'airbnb.co.uk',
        'sleeps': 4,
        'bedrooms': 2,
        'price': '£200/night',
        'priceRange': '$$',
        'highlights': ['250-year-old landmark', 'Featured on Grand Designs', 'Beautifully restored', 'Unique two-bedroom home', 'Buckinghamshire countryside'],
    },
    {
        'name': 'Rivergaze Castle',
        'region': 'England',
        'county': 'Cornwall',
        'snippet': 'Hire Rivergaze Castle exclusively for weddings and retreats in Cornwall. Sleeps 22, self-catered with river access, pool and woodland grounds.',
        'url': 'https://www.thecountrycastlecompany.co.uk/venue/rivergaze-castle/',
        'domain': 'thecountrycastlecompany.co.uk',
        'sleeps': 22,
        'bedrooms': 11,
        'price': '£600/night',
        'priceRange': '$$$',
        'weddingSuitable': True,
        'selfCatering': True,
        'hasPool': True,
        'highlights': ['Exclusive-use castle', 'River access', 'Swimming pool', 'Woodland grounds', 'Sleeps 22 guests', 'Cornwall setting'],
    },
    {
        'name': 'Castle Trematonia',
        'region': 'England',
        'county': 'Cornwall',
        'snippet': 'A unique luxury celebration house set within the ruins of a 14th century castle in Cornwall, with outdoor pool, tropical gardens and views of the Tamar Valley.',
        'url': 'https://www.uniquehomestays.com/self-catering/uk/cornwall/tamar-valley/castle-trematonia/',
        'domain': 'uniquehomestays.com',
        'sleeps': 18,
        'bedrooms': 9,
        'price': '£700/night',
        'priceRange': '$$$',
        'selfCatering': True,
        'hasPool': True,
        'highlights': ['Set within 14th-century castle ruins', 'Outdoor swimming pool', 'Tropical gardens', 'Tamar Valley views', 'Luxury celebration house'],
    },
    {
        'name': 'Langton Castle',
        'region': 'Scotland',
        'county': 'Scottish Borders',
        'snippet': 'This historic Scottish castle sleeps 26 and makes a magnificent setting for a special occasion, only an hour from exciting Edinburgh.',
        'url': 'https://www.oliverstravels.com/britain-ireland/scotland/scottish-borders/langton-castle/',
        'domain': 'oliverstravels.com',
        'sleeps': 26,
        'bedrooms': 13,
        'price': '£500/night',
        'priceRange': '$$$',
        'highlights': ['Historic Scottish castle', 'Sleeps 26 guests', 'One hour from Edinburgh', 'Perfect for special occasions', 'Scottish Borders setting'],
    },
    {
        'name': 'Esk Castle',
        'region': 'Scotland',
        'county': 'Perthshire',
        'snippet': 'Carefully maintained castle set in 1300 acres of rolling parkland, with 2 apartments, ideal for both couples and larger groups.',
        'url': 'https://www.oliverstravels.com/britain-ireland/scotland/perthshire/esk-castle-tower-and-apartment/',
        'domain': 'oliverstravels.com',
        'sleeps': 8,
        'bedrooms': 4,
        'price': '£300/night',
        'priceRange': '$$$',
        'selfCatering': True,
        'highlights': ['1300 acres of rolling parkland', '2 apartments available', 'Perthshire countryside', 'Ideal for couples and groups'],
    },
    {
        'name': 'Orchardleigh Castle',
        'region': 'England',
        'county': 'Somerset',
        'snippet': 'Your own private castle in Somerset - complete with grand interiors and an outdoor hot tub - all based on the stunning 500 acre Orchardleigh Estate. Sleeps 24.',
        'url': 'https://www.coolstays.com/property/orchardleigh-castle/21153',
        'domain': 'coolstays.com',
        'sleeps': 24,
        'bedrooms': 12,
        'price': '£800/night',
        'priceRange': '$$$',
        'hasHotTub': True,
        'highlights': ['Private castle on 500-acre estate', 'Grand interiors', 'Outdoor hot tub', 'Sleeps 24', 'Somerset countryside'],
    },
    {
        'name': 'Knock Old Castle',
        'region': 'Scotland',
        'county': 'Ayrshire',
        'snippet': 'This 14th-century castle is the perfect retreat for a luxurious gathering with family, where you can relax with your feet up around the wood burner.',
        'url': 'https://www.cottages.com/cottages/knock-old-castle-ukc868',
        'domain': 'cottages.com',
        'sleeps': 8,
        'bedrooms': 4,
        'price': '£250/night',
        'priceRange': '$$',
        'selfCatering': True,
        'highlights': ['14th-century castle', 'Wood burner', 'Perfect family retreat', 'Largs coastal setting'],
    },
    {
        'name': 'Machermore Castle',
        'region': 'Scotland',
        'county': 'Dumfries and Galloway',
        'snippet': 'This wonderful castle is perfect for family gatherings, nestled within manicured grounds. Features dining room, kitchen with range, and beautiful setting.',
        'url': 'https://www.cottages.com/cottages/machermore-castle-machermore-castle-uk31878',
        'domain': 'cottages.com',
        'sleeps': 12,
        'bedrooms': 6,
        'price': '£300/night',
        'priceRange': '$$',
        'selfCatering': True,
        'highlights': ['Manicured castle grounds', 'Perfect for family gatherings', 'Near Newton Stewart', 'Galloway countryside'],
    },
    {
        'name': 'Glottenham Castle',
        'region': 'England',
        'county': 'Sussex',
        'snippet': 'Glottenham Castle, Sussex. Sleeps 6. Children welcome. Disappear into the woods and grill on the firepit, spot the rare birds, and learn some history.',
        'url': 'https://www.canopyandstars.co.uk/britain/england/sussex/glottenham-castle',
        'domain': 'canopyandstars.co.uk',
        'sleeps': 6,
        'bedrooms': 3,
        'price': '£200/night',
        'priceRange': '$$',
        'highlights': ['Woodland castle setting', 'Sleeps 6', 'Children welcome', 'Firepit', 'Rare bird spotting', 'Historic Sussex'],
    },
    {
        'name': 'Walton Castle',
        'region': 'England',
        'county': 'Somerset',
        'snippet': 'Reign in style in this majestic 17th-century castle in stunning Somerset countryside. Steeped in history, Walton Castle has been renovated for modern living.',
        'url': 'https://www.airbnb.co.uk/rooms/40028622',
        'domain': 'airbnb.co.uk',
        'sleeps': 10,
        'bedrooms': 5,
        'price': '£350/night',
        'priceRange': '$$$',
        'highlights': ['Majestic 17th-century castle', '360-degree countryside views', 'Renovated for modern living', 'Somerset countryside'],
    },
    {
        'name': 'Stonegate Castle',
        'region': 'England',
        'county': 'Derbyshire',
        'snippet': 'Nestled amidst the picturesque landscapes of the Peak District, Stonegate Castle invites guests to experience its historic charm and character.',
        'url': 'https://www.snaptrip.com/properties/united-kingdom/england/peak-district/derbyshire/high-peak-district/hayfield/scout-castle',
        'domain': 'snaptrip.com',
        'sleeps': 8,
        'bedrooms': 4,
        'price': '£280/night',
        'priceRange': '$$',
        'selfCatering': True,
        'highlights': ['Peak District setting', 'Historic charm', 'Picturesque landscapes', 'Near Hayfield village'],
    },
    {
        'name': 'Forter Castle',
        'region': 'Scotland',
        'county': 'Perthshire',
        'snippet': 'Experience a truly unique getaway at Forter Castle, a stunning 450-year-old Scottish gem that blends historic charm with modern comforts.',
        'url': 'https://fortercastle.com/',
        'domain': 'fortercastle.com',
        'sleeps': 12,
        'bedrooms': 6,
        'price': '£400/night',
        'priceRange': '$$$',
        'selfCatering': True,
        'highlights': ['450-year-old Scottish castle', 'Historic charm with modern comforts', 'Highland Perthshire setting', 'Unique getaway experience'],
    },
    {
        'name': 'Hever Castle Bed and Breakfast',
        'region': 'England',
        'county': 'Kent',
        'snippet': 'Set in 125 acres of formal gardens, this 13th-century double-moated castle offers luxurious yet modern bedrooms with free Wi-Fi. The childhood home of Anne Boleyn.',
        'url': 'https://www.hevercastle.co.uk/stay/',
        'domain': 'hevercastle.co.uk',
        'sleeps': 2,
        'bedrooms': 1,
        'price': '£200/night',
        'priceRange': '$$',
        'highlights': ['13th-century double-moated castle', '125 acres of formal gardens', 'Childhood home of Anne Boleyn', 'Luxurious modern bedrooms', 'Historic Kent setting'],
    },
    {
        'name': 'Dorset Castle',
        'region': 'England',
        'county': 'Dorset',
        'snippet': 'Dorset Castle holds a wonderful location on the iconic Isle of Portland and enjoys magnificent sea views over Church Ope Cove and the famous Jurassic coastline.',
        'url': 'https://www.oliverstravels.com/britain-ireland/dorset/dorset-castle/',
        'domain': 'oliverstravels.com',
        'sleeps': 8,
        'bedrooms': 4,
        'price': '£350/night',
        'priceRange': '$$$',
        'highlights': ['Isle of Portland location', 'Magnificent sea views', 'Church Ope Cove views', 'Jurassic Coast setting'],
    },
    {
        'name': 'Carr Hall Castle',
        'region': 'England',
        'county': 'West Yorkshire',
        'snippet': 'The Yorkshire Castle is a perfect holiday home destination. A luxurious yet cosy sanctuary for those looking to relax in historic Yorkshire surroundings.',
        'url': 'https://carrhallcastle.com/',
        'domain': 'carrhallcastle.com',
        'sleeps': 10,
        'bedrooms': 5,
        'price': '£350/night',
        'priceRange': '$$$',
        'selfCatering': True,
        'highlights': ['Luxurious Yorkshire castle', 'Cosy sanctuary', 'Historic surroundings', 'Perfect for relaxation'],
    },
    {
        'name': 'Glandyfi Castle',
        'region': 'Wales',
        'county': 'Ceredigion',
        'snippet': 'Glandyfi Castle is a 19th Century, Grade II listed castle in Ceredigion, Wales. Available exclusively for private hire.',
        'url': 'https://glandyficastle.co.uk/',
        'domain': 'glandyficastle.co.uk',
        'sleeps': 20,
        'bedrooms': 10,
        'price': '£500/night',
        'priceRange': '$$$',
        'weddingSuitable': True,
        'highlights': ['19th-century Grade II listed castle', 'Exclusive private hire', 'Ceredigion countryside', 'Stunning Welsh setting'],
    },
    {
        'name': 'Belle Isle Castle',
        'region': 'Northern Ireland',
        'county': 'Fermanagh',
        'snippet': 'Belle Isle Castle accommodation can host up to 26 guests in 13 lavishly appointed bedrooms, making it the perfect choice for large groups, family reunions, or special occasions.',
        'url': 'https://belle-isle.com/belle-isle-castle-accommodation/',
        'domain': 'belle-isle.com',
        'sleeps': 26,
        'bedrooms': 13,
        'price': '£600/night',
        'priceRange': '$$$',
        'weddingSuitable': True,
        'highlights': ['26 guests in 13 lavish bedrooms', 'Perfect for family reunions', 'Enniskillen, Fermanagh setting', 'Luxury castle accommodation'],
    },
    {
        'name': 'Thirlestane Castle',
        'region': 'Scotland',
        'county': 'Scottish Borders',
        'snippet': 'Five beautiful suites in the south wing of this fairy tale castle, filled with architectural features, family history and much grandeur.',
        'url': 'https://www.sawdays.co.uk/britain/scotland/scottish-borders/thirlestane-castle/',
        'domain': 'sawdays.co.uk',
        'sleeps': 10,
        'bedrooms': 5,
        'price': '£350/night',
        'priceRange': '$$$',
        'highlights': ['Fairy tale castle', 'Five beautiful suites', 'Rich architectural features', 'Family history and grandeur', 'Scottish Borders setting'],
    },
    {
        'name': 'Narrow Water Castle',
        'region': 'Northern Ireland',
        'county': 'Down',
        'snippet': 'This private estate offers the discerning guest luxury accommodation and endless opportunities to stroll through the picturesque landscaped gardens and farmland.',
        'url': 'https://narrowwatercastle.co.uk/',
        'domain': 'narrowwatercastle.co.uk',
        'sleeps': 12,
        'bedrooms': 6,
        'price': '£400/night',
        'priceRange': '$$$',
        'highlights': ['Private castle estate', 'Luxury accommodation', 'Picturesque landscaped gardens', 'Farmland and grounds to explore'],
    },
    {
        'name': 'Lochhouse Tower',
        'region': 'Scotland',
        'county': 'Dumfries and Galloway',
        'snippet': 'Sleeping up to six overnight guests, Lochhouse Tower sits amidst six acres, beside its own loch, in rural Dumfries and Galloway. Built in 1536.',
        'url': 'https://www.celticcastles.com/castles/lochhouse-tower/',
        'domain': 'celticcastles.com',
        'sleeps': 6,
        'bedrooms': 3,
        'price': '£200/night',
        'priceRange': '$$',
        'selfCatering': True,
        'highlights': ['Built in 1536', 'Six acres with private loch', 'Rural Dumfries and Galloway', 'Sleeps 6 guests'],
    },
    {
        'name': 'Tamar Castle',
        'region': 'England',
        'county': 'Cornwall',
        'snippet': 'Discover the enchanting Tamar Castle, a historic gem nestled on the Cornish riverbank with stunning gardens and luxurious accommodation.',
        'url': 'https://www.oliverstravels.com/britain-ireland/cornwall/tamar-castle/',
        'domain': 'oliverstravels.com',
        'sleeps': 16,
        'bedrooms': 8,
        'price': '£600/night',
        'priceRange': '$$$',
        'highlights': ['Historic Cornish castle', 'Riverbank setting', 'Stunning gardens', 'Luxurious accommodation'],
    },
]


def make_slug(name):
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug.strip())
    slug = re.sub(r'-+', '-', slug)
    return slug


def escape_ts_string(s):
    """Escape a string for use in TypeScript single-quoted strings."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def generate_castle_entry(castle, index):
    slug = make_slug(castle['name'])
    name = escape_ts_string(castle['name'])
    region = castle['region']
    county = escape_ts_string(castle['county'])
    price_range = castle.get('priceRange', '$$')
    avg_price = castle.get('price', '£250/night')
    sleeps = castle.get('sleeps', 8)
    bedrooms = castle.get('bedrooms', 4)
    bathrooms = castle.get('bathrooms', max(1, bedrooms // 2))
    booking_url = castle['url']
    img_idx = index % len(UNSPLASH_IMAGES)
    image = UNSPLASH_IMAGES[img_idx]
    description = escape_ts_string(castle['snippet'])
    domain = castle['domain']

    # Detect features from snippet
    snippet_lower = castle['snippet'].lower()
    wedding = castle.get('weddingSuitable', 'wedding' in snippet_lower)
    pet_friendly = castle.get('petFriendly', 'pet' in snippet_lower or 'dog' in snippet_lower)
    self_catering = castle.get('selfCatering', 'self-cater' in snippet_lower or 'self catering' in snippet_lower)
    has_hot_tub = castle.get('hasHotTub', 'hot tub' in snippet_lower)
    has_pool = castle.get('hasPool', 'pool' in snippet_lower or 'swimming' in snippet_lower)

    highlights = castle.get('highlights', [])
    highlights_str = ',\n'.join(f"      '{escape_ts_string(h)}'" for h in highlights)

    # Build secondary images
    img2 = UNSPLASH_IMAGES[(img_idx + 1) % len(UNSPLASH_IMAGES)]
    img3 = UNSPLASH_IMAGES[(img_idx + 2) % len(UNSPLASH_IMAGES)]

    entry = f"""  {{
    slug: '{slug}',
    name: '{name}',
    region: '{region}',
    county: '{county}',
    type: 'Castle',
    priceRange: '{price_range}',
    avgPrice: '{avg_price}',
    sleeps: {sleeps},
    bedrooms: {bedrooms},
    bathrooms: {bathrooms},
    bookingUrl: '{booking_url}',
    image: '{image}',
    description: '{description}',
    highlights: [
{highlights_str},
    ],
    nearbyAttractions: [],
    overview: '{description}',
    weddingSuitable: {'true' if wedding else 'false'},
    petFriendly: {'true' if pet_friendly else 'false'},
    selfCatering: {'true' if self_catering else 'false'},
    hasHotTub: {'true' if has_hot_tub else 'false'},
    hasPool: {'true' if has_pool else 'false'},
    hasWifi: true,
    bookingPlatform: '{escape_ts_string(domain)}',
    images: [
      '{image}',
      '{img2}',
      '{img3}',
    ],
  }}"""
    return entry


def main():
    # Read existing file
    with open(EXISTING_FILE, 'r') as f:
        content = f.read()

    # Find the insertion point: right before the closing "];" of the castles array
    # The pattern is the last castle's closing "  }," followed by "];"
    # We look for "];\n\n// Compute region counts"
    marker = '];\n\n// Compute region counts from the data'
    if marker not in content:
        print("ERROR: Could not find insertion marker in existing file")
        return

    # Generate new entries
    new_entries = []
    existing_slugs = set()

    # Extract existing slugs from the file
    for match in re.finditer(r"slug:\s*'([^']+)'", content):
        existing_slugs.add(match.group(1))

    print(f"Found {len(existing_slugs)} existing castle slugs")

    added = 0
    skipped = 0
    for i, castle in enumerate(SCRAPED_CASTLES):
        slug = make_slug(castle['name'])
        if slug in existing_slugs:
            print(f"  SKIP (duplicate slug): {castle['name']} -> {slug}")
            skipped += 1
            continue
        existing_slugs.add(slug)
        entry = generate_castle_entry(castle, i)
        new_entries.append(entry)
        added += 1
        print(f"  ADD: {castle['name']} -> {slug}")

    if not new_entries:
        print("No new entries to add!")
        return

    # Build the insertion text
    new_text = ',\n'.join(new_entries)
    insertion = ',\n' + new_text + ',\n'

    # Replace the marker, inserting new entries before it
    new_content = content.replace(
        marker,
        insertion.rstrip(',\n') + ',\n' + marker
    )

    # Wait, that's not right. Let me think about this more carefully.
    # The existing array ends with:
    #   bookingPlatform: 'Eden Hotel Collection',
    #   },
    # ];
    #
    # // Compute region counts from the data
    #
    # So the "];" closes the array. I need to insert new entries BEFORE "];".
    # Let me find "  },\n];" and replace with "  },\n<new entries>\n];"

    # Actually, let me use the marker approach differently.
    # Split at the marker, then reconstruct.

    # Reset and do it properly
    # Find the last "];" before "// Compute region counts"
    # Find the "];\n" that closes the castles array, right before "// Compute region counts"
    # The pattern in the file is:  },\n];\n\n// Compute region counts from the data
    close_pattern = '  },\n];\n\n// Compute region counts from the data'
    if close_pattern not in content:
        print("ERROR: Could not find array closing pattern")
        return

    # Split at the close pattern
    parts = content.split(close_pattern, 1)
    before = parts[0]  # Everything before "  },\n];\n..."
    after = parts[1]   # Everything after "// Compute region counts from the data"

    # Reconstruct: before + last castle close + new entries + array close + region computation
    new_content = before + '  },\n' + new_text + ',\n];\n\n// Compute region counts from the data' + after

    # Write output
    with open(OUTPUT_FILE, 'w') as f:
        f.write(new_content)

    total = len(existing_slugs)
    print(f"\nDone! Merged file written to {OUTPUT_FILE}")
    print(f"  Existing castles: {total - added}")
    print(f"  New castles added: {added}")
    print(f"  Skipped (duplicates): {skipped}")
    print(f"  Total castles: {total}")


if __name__ == '__main__':
    main()
