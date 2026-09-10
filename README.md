探山
探山 is a conversational planning Agent for domestic travel within China. Users can directly describe the departure location, destination, number of days, number of travelers, budget and preferences. The system will generate detailed transportation connections, day-by-day itineraries, landing budgets and pitfall-avoidance tips, along with packing checklists. Within the same session, adjustments such as "change to a 5-day trip" or "switch budget to economy" are supported.
Functional Structure
text
Tanshan/
├── agents/                 # Conversational travel Agent
├── config/                 # DeepSeek, Amap and application configurations
├── core/                   # DeepSeek API client
├── messaging/              # Session state
├── models/                 # Conversation, itinerary, budget and map data models
├── prompts/                # Structured travel planning prompt templates
├── services/               # Demand parsing, local planning, map routing, AI planning
├── skills/                 # 11 travel feature skills
├── static/                 # Frontend styles, scripts and real mountain road assets
├── templates/              # Single-page frontend
├── tests/                  # Unit tests
├── app.py                  # FastAPI application and APIs
└── main.py                 # Launch service and open frontend
Installation & Startup
Run the following commands under D:\gongneng\Tanshan2:
powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python main.py
python main.py starts the service and opens http://127.0.0.1:8000. To start only the service without opening browser:
powershell
python main.py --no-browser
API documentation is available at http://127.0.0.1:8000/docs.
Configuration
Fill in .env as shown below:
dotenv
DEEPSEEK_API_KEY=Your DeepSeek secret key or other AI API KEY
DEEPSEEK_MODEL=deepseek-chat
AMAP_JS_KEY=Your Amap Web JSAPI Key
AMAP_SECURITY_JS_CODE=Corresponding security secret key
Steps for normal Amap integration:
Create an application on Amap Open Platform, add a "Web (JS API)" Key, then copy the security secret key securityJsCode associated with this Key.
Execute Copy-Item .env.example .env in the project directory.
Replace AMAP_JS_KEY and AMAP_SECURITY_JS_CODE with real values, save the file and restart python main.py.
Open the Amap Map panel; self-driving routes use Amap road planning, while high-speed rail, train and flight routes use geocoding and hub route visualization.
If only the Key is filled without the security secret key, JSAPI v2.0 will fail authentication. Do not paste Key and security secret key into chat messages or commit them to code repositories. For production deployment, follow Amap documentation and use serviceHost proxy.
If DeepSeek is not configured, the local planner will be used automatically. Conversation, transportation details, daily itineraries, budgets and packing checklists can still be generated. If Amap is not configured, map and real scenic gallery will show configuration prompts instead of simulated maps or AI-generated images.
The frontend UI adopts a dark travel workspace theme with warm amber accent colors and real mountain road scene assets, preserving all original functional panels and session workflows. The homepage mountain road assets are cropped from reference images provided by users, only used for product atmosphere and do not pretend to be photos of destination attractions.
For local development, the Amap security secret key is injected into the frontend via template. For production deployment, use serviceHost proxy following Amap security specifications to avoid exposing the security secret key.
Map & Gallery
Self-driving: Call AMap.Driving to draw routes based on Amap road data, and display actual returned distance and travel duration.
High-speed rail, train, flight: Use AMap.Geocoder to locate cities and display hub connections. This visualization shall NOT be treated as rail or air navigation.
Scenic gallery: Use AMap.PlaceSearch to search scenic spots within the selected destination. Only render POIs returned by Amap with authentic photos, filtering out results from other cities.
Itinerary Specification
Transportation cards only inform users of departure stations/airports, transfer arrangements and arrival hubs. Ticket prices are NOT displayed. The budget range is calculated based on traveler count, room quantity and trip duration, covering accommodation, catering, tickets, local transit plus a 10% contingency fund. It clearly excludes long-distance outbound transportation.
The project contains 11 skills: weather, route, attractions along the way, budget, local cuisine, dietary restrictions, local customs, festival etiquette, characteristic culture, pitfall avoidance and travel preparation. Travel preparation generates checklists covering documents, clothing, health protection, electronic devices, reservation materials, destination-specific items and pre-departure verification.
Validation

python -m unittest discover -s tests -v
node --check static\app.js
