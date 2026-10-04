"""Small offline gazetteer for header locations (PROMPT.md §5 Stage 8).
Hand-curated, not GeoNames: India-heavy because that's the production
distribution (Indian student resumes), plus common world cities/countries.
Extend by appending; matching is longest-first so "Navi Mumbai" beats "Mumbai".
"""

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Orissa", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Jammu and Kashmir",
    "Ladakh", "Chandigarh", "Puducherry", "Andaman and Nicobar Islands",
]

INDIAN_CITIES = [
    "Mumbai", "Navi Mumbai", "Thane", "Pune", "Delhi", "New Delhi", "Noida", "Gurgaon", "Gurugram", "Faridabad",
    "Ghaziabad", "Bangalore", "Bengaluru", "Hyderabad", "Secunderabad", "Chennai", "Kolkata", "Ahmedabad",
    "Surat", "Vadodara", "Rajkot", "Jaipur", "Jodhpur", "Udaipur", "Kota", "Lucknow", "Kanpur", "Varanasi",
    "Agra", "Allahabad", "Prayagraj", "Meerut", "Nagpur", "Nashik", "Aurangabad", "Kolhapur", "Solapur",
    "Vasai", "Virar", "Kalyan", "Dombivli", "Ulhasnagar", "Panvel", "Bhiwandi", "Mira Road", "Borivali",
    "Andheri", "Bandra", "Powai", "Kandivali", "Malad", "Goregaon", "Vile Parle", "Ghatkopar", "Mulund",
    "Indore", "Bhopal", "Gwalior", "Jabalpur", "Raipur", "Bhilai", "Patna", "Ranchi", "Jamshedpur", "Dhanbad",
    "Bhubaneswar", "Cuttack", "Guwahati", "Shillong", "Imphal", "Kochi", "Cochin", "Thiruvananthapuram",
    "Trivandrum", "Kozhikode", "Calicut", "Thrissur", "Mysore", "Mysuru", "Mangalore", "Mangaluru", "Hubli",
    "Belgaum", "Belagavi", "Coimbatore", "Madurai", "Tiruchirappalli", "Trichy", "Salem", "Tirunelveli",
    "Vellore", "Visakhapatnam", "Vizag", "Vijayawada", "Guntur", "Tirupati", "Warangal", "Chandigarh",
    "Mohali", "Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Dehradun", "Haridwar", "Shimla", "Srinagar",
    "Jammu", "Panaji", "Margao", "Pondicherry", "Puducherry", "Siliguri", "Durgapur", "Howrah", "Ajmer",
    "Bikaner", "Alwar", "Rohtak", "Karnal", "Ambala", "Bareilly", "Aligarh", "Moradabad", "Gorakhpur",
    "Dharwad", "Thanjavur", "Erode", "Nellore", "Rajahmundry", "Kakinada", "Anand", "Bhavnagar", "Jamnagar",
    "Gandhinagar", "Ernakulam", "Kollam", "Palakkad", "Kannur", "Alappuzha", "Pimpri-Chinchwad", "Pimpri", "Chinchwad", "Alibag", "Lonavala", "Satara", "Sangli",
]

WORLD_CITIES = [
    "New York", "Los Angeles", "San Francisco", "San Jose", "Seattle", "Boston", "Chicago", "Austin", "Dallas",
    "Houston", "Atlanta", "Washington", "Philadelphia", "San Diego", "Denver", "Miami", "Toronto", "Vancouver",
    "Montreal", "Ottawa", "London", "Manchester", "Birmingham", "Edinburgh", "Glasgow", "Dublin", "Paris",
    "Berlin", "Munich", "Frankfurt", "Amsterdam", "Madrid", "Barcelona", "Rome", "Milan", "Zurich", "Geneva",
    "Stockholm", "Copenhagen", "Oslo", "Helsinki", "Warsaw", "Prague", "Vienna", "Dubai", "Abu Dhabi",
    "Sharjah", "Doha", "Riyadh", "Jeddah", "Kuwait City", "Muscat", "Singapore", "Hong Kong", "Tokyo", "Osaka",
    "Seoul", "Beijing", "Shanghai", "Shenzhen", "Bangkok", "Kuala Lumpur", "Jakarta", "Manila", "Sydney",
    "Melbourne", "Brisbane", "Perth", "Auckland", "Johannesburg", "Cape Town", "Nairobi", "Lagos", "Cairo",
    "Kampala", "Dhaka", "Karachi", "Lahore", "Kathmandu", "Colombo", "Sao Paulo", "Mexico City", "Buenos Aires",
    "Cambridge", "Oxford", "Baltimore", "Pittsburgh", "Portland", "Phoenix", "Las Vegas",
    "Lafayette", "Baton Rouge", "Nashville", "Charlotte", "Minneapolis", "Detroit", "Columbus", "Raleigh",
]

COUNTRIES = {
    "India": "India", "USA": "USA", "U.S.A.": "USA", "U.S.": "USA", "United States": "USA",
    "United States of America": "USA", "UK": "UK", "U.K.": "UK", "United Kingdom": "UK", "England": "UK",
    "Scotland": "UK", "Canada": "Canada", "Australia": "Australia", "Germany": "Germany", "France": "France",
    "Netherlands": "Netherlands", "Ireland": "Ireland", "Singapore": "Singapore", "UAE": "UAE",
    "United Arab Emirates": "UAE", "Saudi Arabia": "Saudi Arabia", "Qatar": "Qatar", "Japan": "Japan",
    "China": "China", "Sweden": "Sweden", "Switzerland": "Switzerland", "Spain": "Spain", "Italy": "Italy",
    "Nepal": "Nepal", "Bangladesh": "Bangladesh", "Sri Lanka": "Sri Lanka", "Pakistan": "Pakistan",
    "Uganda": "Uganda", "Kenya": "Kenya", "Nigeria": "Nigeria", "South Africa": "South Africa",
    "New Zealand": "New Zealand", "Malaysia": "Malaysia", "Indonesia": "Indonesia", "Philippines": "Philippines",
}

US_STATES = [
    "California", "Texas", "New York", "Florida", "Washington", "Massachusetts", "Illinois", "Georgia",
    "Virginia", "Maryland", "Louisiana", "Pennsylvania", "Ohio", "Michigan", "Colorado", "Arizona",
    "North Carolina", "New Jersey", "Oregon", "Nevada", "Utah", "Minnesota", "Tennessee",
]
