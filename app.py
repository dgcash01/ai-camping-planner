# --- app.py --- (Complete Code - Re-adding /blog route)

from flask import Flask, render_template, request
import requests
import os
import math
import re # For cleaning description HTML
import traceback # For detailed error logging
# import json # Only needed if adding print statements back for debugging
from datetime import datetime # For footer year

app = Flask(__name__)

# --- Configuration ---
REC_GOV_API_KEY = os.environ.get('REC_GOV_API_KEY', None)
RIDB_API_BASE_URL = "https://ridb.recreation.gov/api/v1"

# --- Your Chosen Activity IDs ---
FAMILY_ACTIVITY_IDS = [
    9, 37, 34, 106, 14, 11, 5, 20, 6, 105, 26, 10, 24, 100097, 100085, 100091
]
activity_filter_string = ",".join(map(str, FAMILY_ACTIVITY_IDS))

# --- Context Processor for Year ---
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.utcnow().year}

# --- Routes ---

@app.route('/')
def index():
    """Renders the main HTML page."""
    return render_template('index.html')

# --- ADDED BLOG ROUTE ---
@app.route('/blog')
def blog():
    """Renders the blog page."""
    # The actual content is now in templates/blog.html
    return render_template('blog.html')
# -------------------------

# --- ENHANCED and POLISHED Search Facilities Route ---
@app.route('/search-facilities')
def search_facilities():
    """Searches for facilities using the RIDB API, returns polished HTML with pagination."""

    if not REC_GOV_API_KEY:
        print("API Key Error: REC_GOV_API_KEY environment variable not set.")
        return '<p class="text-red-600 font-semibold text-center py-4">Error: API Key is not configured on the server.</p>'

    try:
        offset = int(request.args.get('offset', 0))
    except ValueError: offset = 0
    try:
        limit = int(request.args.get('limit', 10))
        limit = max(1, min(limit, 50))
    except ValueError: limit = 10

    api_url = f"{RIDB_API_BASE_URL}/facilities"
    params = {"state": "MO", "activity": activity_filter_string, "full": "true", "limit": limit, "offset": offset}
    headers = {"Accept": "application/json", "apikey": REC_GOV_API_KEY}

    try:
        print(f"Calling API: {api_url} | Params: state={params['state']}, limit={limit}, offset={offset}, activity={params['activity'][:50]}...")
        response = requests.get(api_url, headers=headers, params=params, timeout=20)
        response.raise_for_status()

        data = response.json()
        facilities = data.get('RECDATA', [])
        metadata = data.get('METADATA', {})
        results_info = metadata.get('RESULTS', {})
        total_count = results_info.get('TOTAL_COUNT', 0)
        current_count = len(facilities)

        if not facilities and offset == 0: return '<p class="text-center text-gray-600 py-4">No facilities found matching your criteria.</p>'
        elif not facilities: return '<p class="text-center text-gray-600 py-4">No more facilities found.</p>'

        html_output = f'<h3 class="text-lg font-semibold mb-4">Found {total_count} Facilities (Showing {offset + 1}-{offset + current_count}):</h3>'
        html_output += '<div class="space-y-5">'

        for facility in facilities:
            facility_id = facility.get('FacilityID', '')
            if not facility_id: continue

            facility_name = facility.get('FacilityName', 'N/A')
            facility_type = facility.get('FacilityTypeDescription', '')
            description = facility.get('FacilityDescription', '')
            clean_desc = re.sub('<[^>]+>', '', description)
            truncated_desc = (clean_desc[:150] + '...') if len(clean_desc) > 150 else clean_desc

            address_list = facility.get('FACILITYADDRESS', [])
            city, state_code, location = '', '', ''
            if address_list:
                address = next((addr for addr in address_list if addr.get('FacilityAddressType') == 'Default'), address_list[0])
                city = address.get('City', '')
                state_code = address.get('AddressStateCode', '')
            location = f"{city}, {state_code}".strip(', ').upper() if city or state_code else ""

            primary_link, link_text = "#", "No Link Available"
            if facility_type.lower() == 'campground':
                 primary_link = f"https://www.recreation.gov/camping/campgrounds/{facility_id}"
                 link_text = "Check Availability / Details"
            else:
                 link_list = facility.get('LINK', [])
                 official_link_info = next((link for link in link_list if link.get('LinkType') == 'Official Web Site' and link.get('URL')), None)
                 if official_link_info:
                      primary_link = official_link_info['URL']
                      link_text = "Visit Official Website"

            image_url = None
            media_list = facility.get('MEDIA', [])
            if media_list:
                primary_media = next((media for media in media_list if media.get('IsPrimary') and media.get('MediaType') == 'Image' and media.get('URL')), None)
                if primary_media: image_url = primary_media['URL']
                else:
                    first_image = next((media for media in media_list if media.get('MediaType') == 'Image' and media.get('URL')), None)
                    if first_image: image_url = first_image['URL']

            activities_list = facility.get('ACTIVITY', [])
            activity_display_html = ""
            if activities_list:
                 activity_display_html += '<div class="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1">'
                 icon_map = {"CAMPING": "🏕️", "HIKING": "🥾", "FISHING": "🎣", "BOATING": "🛶","SWIMMING": "🏊", "SWIMMING SITE": "🏊", "PICNICKING": "🧺","PLAYGROUND PARK SPECIALIZED SPORT SITE": "🤸", "WILDLIFE VIEWING": " binoculars","VISITOR CENTER": "ℹ️", "INTERPRETIVE PROGRAMS": "🧑‍🏫", "PADDLING": "🛶","AUTO TOURING": "🚗", "BIKING": "🚲", "CLIMBING": "🧗", "HORSEBACK RIDING": "🐎","HUNTING": "🎯", "OFF HIGHWAY VEHICLE": "🚜", "WATER SPORTS": "🌊","HISTORIC & CULTURAL SITE": "🏛️", "PHOTOGRAPHY": "📷", "GEOCACHING": "📍","BIRDING": "🐦", "BIRD WATCHING": "🐦"}
                 displayed_icons = set()
                 for act in activities_list:
                     act_name_upper = act.get('ActivityName', '').upper()
                     icon = icon_map.get(act_name_upper)
                     if icon and icon not in displayed_icons:
                          activity_display_html += f'<span title="{act_name_upper.title()}" class="text-xl">{icon}</span>'
                          displayed_icons.add(icon)
                 if not displayed_icons and activities_list: activity_display_html += '<span class="text-xs text-gray-500">Activities available</span>'
                 activity_display_html += '</div>'

            html_output += f"""
            <div class="border border-gray-200 rounded-lg bg-white shadow-md hover:shadow-lg transition-shadow duration-200 overflow-hidden flex flex-col md:flex-row">
                {f'<div class="md:w-1/3 lg:w-1/4 flex-shrink-0"><img src="{image_url}" alt="{facility_name}" class="w-full h-48 md:h-full object-cover"></div>' if image_url else '<div class="md:w-1/3 lg:w-1/4 flex-shrink-0 bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center h-48 md:h-auto"><span class="text-gray-400 text-lg">🏞️</span></div>'}
                <div class="flex flex-col flex-grow">
                    <div class="p-5 flex-grow">
                        <h4 class="text-lg md:text-xl font-semibold mb-1 text-gray-900">
                            <a href="{primary_link}" target="_blank" rel="noopener noreferrer" class="hover:text-emerald-700 hover:underline">{facility_name}</a>
                        </h4>"""
            type_location_info = f"{facility_type}{' | ' + location if location and facility_type else location}"
            if type_location_info: html_output += f'<p class="text-sm text-gray-500 mb-3">{type_location_info}</p>'
            html_output += f"""
                        <p class="text-gray-800 text-sm mb-3 leading-relaxed">{truncated_desc}</p>
                        {activity_display_html}
                    </div>
                    <div class="bg-gray-50 px-5 py-4 border-t border-gray-200">
                        <a href="{primary_link}" target="_blank" rel="noopener noreferrer"
                           class="inline-block bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium py-2 px-4 rounded-md shadow-sm transition duration-150 ease-in-out {'opacity-50 cursor-not-allowed pointer-events-none' if primary_link == '#' else ''}"
                           aria-disabled="{primary_link == '#'}"
                        >
                            {link_text} &rarr;
                        </a>
                    </div>
                 </div>
            </div>"""
        html_output += '</div>'

        # --- Add Pagination Controls ---
        htmx_common_attrs = f'hx-target="#search-results-area" hx-swap="innerHTML" hx-indicator="#search-loading-spinner, #search-results-area"'
        htmx_include_attr = 'hx-include="#results-limit-select"'
        html_output += '<div class="mt-8 flex justify-between items-center">'
        if offset > 0:
            prev_offset = max(0, offset - limit)
            html_output += f"""<button hx-get="/search-facilities?offset={prev_offset}&limit={limit}" {htmx_common_attrs} {htmx_include_attr} class="bg-gray-500 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded-md shadow-sm transition duration-150 ease-in-out">&laquo; Previous</button>"""
        else: html_output += '<div class="w-28 h-10"></div>'

        total_pages = math.ceil(total_count / limit) if limit > 0 else 1
        current_page = math.ceil((offset + 1) / limit) if limit > 0 else 1
        if total_count > 0: html_output += f'<span class="text-gray-700 font-medium text-sm">Page {current_page} of {total_pages}</span>'
        else: html_output += '<span></span>'

        if offset + current_count < total_count:
            next_offset = offset + limit
            html_output += f"""<button hx-get="/search-facilities?offset={next_offset}&limit={limit}" {htmx_common_attrs} {htmx_include_attr} class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-md shadow-sm transition duration-150 ease-in-out">Next &raquo;</button>"""
        else: html_output += '<div class="w-24 h-10"></div>'
        html_output += '</div>'

        return html_output

    # --- Error Handling ---
    except requests.exceptions.Timeout: print("API Request Error: Timeout"); return '<p class="text-red-600 font-semibold text-center py-4">Error: The request to Recreation.gov timed out. Please try again later.</p>'
    except requests.exceptions.HTTPError as e: print(f"API Request Error: HTTPError - Status {e.response.status_code}, Response: {e.response.text[:200]}..."); error_detail = f"Status Code: {e.response.status_code}."; error_detail += " Please check if the API key is correct and properly configured." if e.response.status_code in [401, 403] else ""; return f'<p class="text-red-600 font-semibold text-center py-4">Error contacting Recreation.gov API. {error_detail}</p>'
    except requests.exceptions.RequestException as e: print(f"API Request Error: {e}"); return f'<p class="text-red-600 font-semibold text-center py-4">Error contacting Recreation.gov API: {e}</p>'
    except Exception as e: print(f"Error processing API response: {e}"); traceback.print_exc(); return f'<p class="text-red-600 font-semibold text-center py-4">An unexpected error occurred processing the data: {e}</p>'

# Basic run command
if __name__ == '__main__':
    app.run(debug=True)