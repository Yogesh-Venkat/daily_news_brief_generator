# API Testing Examples

This file contains examples for testing the Daily News Brief Generator API.

## Using curl

### 1. Health Check
```bash
curl http://localhost:8000/health
```

Expected Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00"
}
```

### 2. Get Categories
```bash
curl http://localhost:8000/categories
```

Expected Response:
```json
{
  "categories": [
    "Technology",
    "Business",
    "Sports",
    "Health",
    "Entertainment",
    "Politics"
  ]
}
```

### 3. Save User Preferences
```bash
curl -X POST http://localhost:8000/preferences \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "default_user",
    "segments": ["Technology", "Business"],
    "reading_preference": "short",
    "language": "en"
  }'
```

Expected Response:
```json
{
  "message": "Preferences saved successfully",
  "preferences": {
    "user_id": "default_user",
    "segments": ["Technology", "Business"],
    "reading_preference": "short",
    "language": "en"
  }
}
```

### 4. Get User Preferences
```bash
curl http://localhost:8000/preferences/default_user
```

Expected Response:
```json
{
  "user_id": "default_user",
  "segments": ["Technology", "Business"],
  "reading_preference": "short",
  "language": "en"
}
```

### 5. Get News Brief (All Categories)
```bash
curl -X POST http://localhost:8000/news-brief \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "default_user"
  }'
```

### 6. Get News Brief (Specific Category)
```bash
curl -X POST http://localhost:8000/news-brief \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "default_user",
    "category": "Technology"
  }'
```

### 7. Get News Brief (Specific Date)
```bash
curl -X POST http://localhost:8000/news-brief \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "default_user",
    "date": "2024-01-01"
  }'
```

## Using Python requests

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# 1. Health Check
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# 2. Get Categories
response = requests.get(f"{BASE_URL}/categories")
print(response.json())

# 3. Save Preferences
preferences = {
    "user_id": "test_user",
    "segments": ["Technology", "Business", "Sports"],
    "reading_preference": "short",
    "language": "en"
}
response = requests.post(f"{BASE_URL}/preferences", json=preferences)
print(response.json())

# 4. Get Preferences
response = requests.get(f"{BASE_URL}/preferences/test_user")
print(response.json())

# 5. Get News Brief
brief_request = {
    "user_id": "test_user",
    "category": "Technology"
}
response = requests.post(f"{BASE_URL}/news-brief", json=brief_request)
briefs = response.json()
print(json.dumps(briefs, indent=2))
```

## Using JavaScript (Node.js)

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000';

async function testAPI() {
  try {
    // 1. Health Check
    let response = await axios.get(`${BASE_URL}/health`);
    console.log('Health:', response.data);

    // 2. Get Categories
    response = await axios.get(`${BASE_URL}/categories`);
    console.log('Categories:', response.data);

    // 3. Save Preferences
    const preferences = {
      user_id: 'test_user',
      segments: ['Technology', 'Business'],
      reading_preference: 'short',
      language: 'en'
    };
    response = await axios.post(`${BASE_URL}/preferences`, preferences);
    console.log('Saved Preferences:', response.data);

    // 4. Get News Brief
    const briefRequest = {
      user_id: 'test_user',
      category: 'Technology'
    };
    response = await axios.post(`${BASE_URL}/news-brief`, briefRequest);
    console.log('News Brief:', JSON.stringify(response.data, null, 2));

  } catch (error) {
    console.error('Error:', error.message);
  }
}

testAPI();
```

## Using Postman

### Import Collection

Create a new Postman collection with these requests:

#### 1. Health Check
- Method: GET
- URL: `http://localhost:8000/health`

#### 2. Get Categories
- Method: GET
- URL: `http://localhost:8000/categories`

#### 3. Save Preferences
- Method: POST
- URL: `http://localhost:8000/preferences`
- Headers: `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "user_id": "default_user",
  "segments": ["Technology", "Business"],
  "reading_preference": "short",
  "language": "en"
}
```

#### 4. Get Preferences
- Method: GET
- URL: `http://localhost:8000/preferences/default_user`

#### 5. Get News Brief
- Method: POST
- URL: `http://localhost:8000/news-brief`
- Headers: `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "user_id": "default_user",
  "category": "Technology",
  "date": "2024-01-01"
}
```

## Testing Scenarios

### Scenario 1: New User Flow
```bash
# 1. Check if preferences exist
curl http://localhost:8000/preferences/new_user

# 2. Save new preferences
curl -X POST http://localhost:8000/preferences \
  -H "Content-Type: application/json" \
  -d '{"user_id":"new_user","segments":["Technology"]}'

# 3. Get news brief
curl -X POST http://localhost:8000/news-brief \
  -H "Content-Type: application/json" \
  -d '{"user_id":"new_user"}'
```

### Scenario 2: Update Preferences
```bash
# 1. Get current preferences
curl http://localhost:8000/preferences/default_user

# 2. Update preferences
curl -X POST http://localhost:8000/preferences \
  -H "Content-Type: application/json" \
  -d '{"user_id":"default_user","segments":["Technology","Business","Sports"]}'

# 3. Verify update
curl http://localhost:8000/preferences/default_user
```

### Scenario 3: Date-based News
```bash
# Get news from yesterday
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
curl -X POST http://localhost:8000/news-brief \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"default_user\",\"date\":\"$YESTERDAY\"}"
```

### Scenario 4: Category Filtering
```bash
# Get only Technology news
curl -X POST http://localhost:8000/news-brief \
  -H "Content-Type: application/json" \
  -d '{"user_id":"default_user","category":"Technology"}'

# Get only Business news
curl -X POST http://localhost:8000/news-brief \
  -H "Content-Type: application/json" \
  -d '{"user_id":"default_user","category":"Business"}'
```

## Load Testing

### Using Apache Bench (ab)
```bash
# Install ab (usually comes with Apache)
# Test health endpoint
ab -n 100 -c 10 http://localhost:8000/health

# Test categories endpoint
ab -n 100 -c 10 http://localhost:8000/categories
```

### Using wrk
```bash
# Install wrk
# Test for 30 seconds with 10 connections
wrk -t10 -c10 -d30s http://localhost:8000/health
```

## Expected Response Times

- Health Check: < 50ms
- Get Categories: < 50ms
- Save Preferences: < 100ms
- Get Preferences: < 100ms
- Get News Brief: 2-5 seconds (includes API calls and AI processing)

## Common Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error message"
}
```

## Debugging Tips

1. **Check Backend Logs**: View terminal running the backend
2. **Use Verbose Mode**: Add `-v` to curl commands
3. **Check Network**: Ensure backend is running on correct port
4. **Validate JSON**: Use a JSON validator for request bodies
5. **Check API Docs**: Visit http://localhost:8000/docs

## Integration Testing Script

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"
USER_ID="test_$(date +%s)"

echo "Testing Daily News Brief Generator API"
echo "======================================"

# Test 1: Health Check
echo -e "\n1. Testing Health Check..."
curl -s $BASE_URL/health | jq

# Test 2: Get Categories
echo -e "\n2. Testing Get Categories..."
curl -s $BASE_URL/categories | jq

# Test 3: Save Preferences
echo -e "\n3. Testing Save Preferences..."
curl -s -X POST $BASE_URL/preferences \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"$USER_ID\",\"segments\":[\"Technology\",\"Business\"]}" | jq

# Test 4: Get Preferences
echo -e "\n4. Testing Get Preferences..."
curl -s $BASE_URL/preferences/$USER_ID | jq

# Test 5: Get News Brief
echo -e "\n5. Testing Get News Brief..."
curl -s -X POST $BASE_URL/news-brief \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"$USER_ID\"}" | jq -c '.briefs[0].category, .briefs[0].articles | length'

echo -e "\nAll tests completed!"
```

Save this as `test_api.sh`, make it executable (`chmod +x test_api.sh`), and run it.
