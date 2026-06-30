# Meal Planning Agent

An autonomous AI agent designed to automate meal planning, recipe discovery, grocery scheduling, and food ordering, while respecting your personal dietary preferences, allergies, and restrictions.

Built using the **Google Antigravity SDK**.

## Features

1. **Persistent User Profile**: Remembers your food preferences, allergies, and dietary restrictions in a local `user_profile.json` file. It automatically updates this profile when you share new preferences.
2. **Google Calendar Integration**: Can view your schedule to find free slots and automatically schedule meals, cooking sessions, or grocery shopping trips.
3. **Web Search Integration**: Uses DuckDuckGo Search (no API keys required!) to find recipes, cooking ideas, local grocery stores, or restaurants.
4. **Payment Safety Policy**: Intercepts any payment requests (e.g., ordering groceries or takeout) and prompts you in the terminal for explicit approval (`yes`/`no`) before spending any money.
5. **Agent-to-Agent (A2A) Delegation**: Can spawn specialized subagents to perform complex subtasks (e.g., deep recipe research or nutritional analysis) in the background.

---

## File Structure

- [meal_planning_agent.py](file:///Users/xinyingli/Project/5-day-Lab/meal_planning_agent.py): The main script that configures the agent, defines the safety policies, and runs the interactive chat loop.
- [tools/](file:///Users/xinyingli/Project/5-day-Lab/tools/):
  - [tools/profile_tools.py](file:///Users/xinyingli/Project/5-day-Lab/tools/profile_tools.py): Handles reading and writing the user profile.
  - [tools/calendar_tools.py](file:///Users/xinyingli/Project/5-day-Lab/tools/calendar_tools.py): Interfaces with the Google Calendar API.
  - [tools/search_tools.py](file:///Users/xinyingli/Project/5-day-Lab/tools/search_tools.py): Performs web searches.
  - [tools/payment_tools.py](file:///Users/xinyingli/Project/5-day-Lab/tools/payment_tools.py): Mock payment processing tool.
- [requirements.txt](file:///Users/xinyingli/Project/5-day-Lab/requirements.txt): Python dependencies.

---

## Setup Instructions

### 1. Install Dependencies

If you haven't already, install the required Python packages:
```bash
pip install -r requirements.txt
```
*Note: If you encounter issues with a custom index, you can force install from the public PyPI registry:*
```bash
pip install duckduckgo_search --index-url https://pypi.org/simple --user
```

### 2. Configure Google Calendar (Optional but Recommended)

To allow the agent to schedule meals on your calendar:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one).
3. Search for and enable the **Google Calendar API**.
4. Configure the **OAuth Consent Screen** (set User Type to *External* and add your email as a test user).
5. Go to **Credentials** -> **Create Credentials** -> **OAuth client ID**.
6. Select **Desktop App** as the Application type, name it, and click Create.
7. Click the download icon next to your client ID to download the JSON file.
8. Rename the downloaded file to `credentials.json` and place it in this project's root directory (`/Users/xinyingli/Project/5-day-Lab/credentials.json`).

*Note: The first time the agent attempts to access your calendar, a browser window will open asking you to log in and authorize the application. Once authorized, a `token.json` file will be saved locally to keep you logged in.*

---

## How to Run

Start the interactive session by running:
```bash
python3 meal_planning_agent.py
```

### Example Prompts to Try:

- **Managing Profile**: 
  - `"I am allergic to peanuts and I prefer spicy food. Please update my profile."`
  - `"What are my current dietary restrictions?"`
- **Searching Recipes**:
  - `"Find me a quick 20-minute vegetarian dinner recipe."`
- **Scheduling**:
  - `"What do I have scheduled for tomorrow?"`
  - `"Schedule a cooking session for Vegan Chili tomorrow at 6 PM."`
- **Purchasing (Testing the Safety Policy)**:
  - `"Order a weekly grocery list of ingredients for the Vegan Chili from Whole Foods for $45.50."`
  *(You will see a terminal prompt asking for your approval before the payment is processed!)*
- **Delegation**:
  - `"Use a specialized subagent to analyze the nutritional value of a classic lasagna recipe."`

---

## CI/CD & Deployment

For detailed instructions on running tests, linting, Docker containerization, and the GitHub Actions CI/CD pipeline, please refer to the [DEPLOYMENT.md](file:///Users/xinyingli/Project/AITraining1/DEPLOYMENT.md) guide.

