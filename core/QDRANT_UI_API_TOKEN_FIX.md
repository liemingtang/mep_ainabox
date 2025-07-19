# Qdrant UI API Token Fix

## Problem Description

When accessing the Qdrant Database Manager at `http://localhost:7070/index.html`, users were getting the error:

```
Error: Unexpected token 'M', "Must provi"... is not valid JSON
```

This error occurred because Qdrant requires an API key for authentication, but the Qdrant UI was not configured to pass the API token to the Qdrant API.

Additionally, when trying to create collections, users would get an empty error message:

```
Error: 
```

This was caused by using the wrong HTTP method for collection creation.

Furthermore, when navigating to the Qdrant UI, existing collections were not being displayed automatically, requiring users to manually click the "Collections" tab to see them.

## Root Cause

1. **Qdrant API Authentication**: Qdrant is configured to require an API key for all operations
2. **Missing API Token**: The Qdrant UI was making direct API calls without authentication
3. **Dashboard Integration**: The dashboard was not passing the API token when launching the Qdrant UI
4. **Wrong HTTP Method**: Collection creation was using POST instead of PUT method
5. **Poor Error Handling**: Empty error responses were not being handled properly
6. **Missing Auto-Load**: Collections were not being loaded automatically on page load

## Solution Implemented

### 1. Enhanced Qdrant UI with API Token Support

**File**: `mep_ainabox/services/qdrant-ui/index.html`

**Changes Made**:
- Added API token input field with visibility toggle
- Added connection test functionality
- Modified all API calls to include the `api-key` header
- Added URL parameter support for automatic token loading
- Enhanced error handling and user feedback
- **Fixed collection creation to use PUT method instead of POST**
- **Improved error message parsing for better debugging**
- **Added automatic collections loading on page load**

**Key Features**:
- **API Token Input**: Secure password field for entering the Qdrant API token
- **Visibility Toggle**: Show/hide the API token for easy verification
- **Test Connection**: Verify the API token works before proceeding
- **Auto-Load**: Automatically load API token from URL parameters
- **Clear Function**: Remove stored API token for security
- **Proper Error Messages**: Better error handling with detailed messages
- **Auto-Load Collections**: Collections are automatically loaded when the page loads

### 2. Dashboard Integration

**File**: `mep_ainabox/core/dashboard/main.py`

**Changes Made**:
- Modified Qdrant UI service configuration to include API token in URL
- Updated both infrastructure and admin UI service lists
- Ensured consistent API token passing across all Qdrant-related links

**Configuration**:
```python
# Before
{"name": "Qdrant UI", "admin_url": "http://localhost:7070/index.html"}

# After  
{"name": "Qdrant UI", "admin_url": f"http://localhost:7070/index.html?api_token={QDRANT_API_KEY}"}
```

## How It Works

### 1. Dashboard Launch
When users click "Open" next to "Qdrant UI" in the dashboard admin panel:
1. Dashboard generates URL with API token: `http://localhost:7070/index.html?api_token=qdrant_api_key`
2. Qdrant UI loads and automatically extracts the API token from URL parameters
3. API token is pre-filled in the input field
4. Connection is automatically tested

### 2. Manual Access
Users can also access the Qdrant UI directly:
1. Navigate to `http://localhost:7070/index.html`
2. Enter the API token manually: `qdrant_api_key`
3. Click "Test Connection" to verify
4. Use all Qdrant UI features with proper authentication

### 3. API Calls
All Qdrant API calls from the UI now include the API token:
```javascript
function getHeaders() {
    const headers = {
        'Content-Type': 'application/json'
    };
    if (apiToken) {
        headers['api-key'] = apiToken;
    }
    return headers;
}
```

### 4. Collection Creation
Collections are now created using the correct PUT method:
```javascript
// Before (incorrect)
const response = await fetch(`${QDRANT_URL}/collections`, {
    method: 'POST',
    body: JSON.stringify({
        name: name,
        vectors: { size: size, distance: distance }
    })
});

// After (correct)
const response = await fetch(`${QDRANT_URL}/collections/${name}`, {
    method: 'PUT',
    body: JSON.stringify({
        vectors: { size: size, distance: distance }
    })
});
```

### 5. Auto-Loading Collections
Collections are now automatically loaded when the page loads:
```javascript
// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // ... API token setup ...
    
    // Load initial data
    loadStatus();
    loadCollections();  // Added this line
});

// Also load collections after successful connection test
async function testConnection() {
    // ... connection test ...
    if (response.ok) {
        // ... success message ...
        loadStatus();
        loadCollections();  // Added this line
    }
}
```

## Testing

### Automated Test
Run the test script to verify the fix:
```bash
cd mep_ainabox/core
python3 test_qdrant_ui_fix.py
python3 test_qdrant_collection_fix.py
python3 test_qdrant_collections_loading.py
```

### Manual Testing
1. **Dashboard Access**:
   - Go to `http://localhost:8010/admin`
   - Click "Open" next to "Qdrant UI"
   - Verify API token is pre-filled
   - Click "Test Connection"

2. **Collection Creation**:
   - Go to the "Collections" tab
   - Enter collection name: "test1"
   - Set vector size: 1536
   - Select distance metric: "Cosine"
   - Click "Create Collection"
   - Should see "Collection created successfully!"

3. **Collections Display**:
   - Navigate to `http://localhost:7070/index.html?api_token=qdrant_api_key`
   - Collections should load automatically
   - Check the "Collections" tab to see all existing collections
   - Check the "Search" and "Points" tabs to see collection dropdowns populated

4. **Direct Access**:
   - Go to `http://localhost:7070/index.html`
   - Enter API token: `qdrant_api_key`
   - Click "Test Connection"
   - Verify collections load correctly

5. **API Verification**:
   ```bash
   # Test without API key (should fail)
   curl http://localhost:6333/collections
   
   # Test with API key (should succeed)
   curl -H "api-key: qdrant_api_key" http://localhost:6333/collections
   
   # Test collection creation (should work)
   curl -H "api-key: qdrant_api_key" -X PUT "http://localhost:6333/collections/test1" \
     -H "Content-Type: application/json" \
     -d '{"vectors": {"size": 1536, "distance": "Cosine"}}'
   ```

## Configuration

### Environment Variables
The API token is configured in the dashboard environment:
```bash
QDRANT_API_KEY=qdrant_api_key
```

### Qdrant Configuration
The Qdrant service is configured to require API authentication in the docker-compose file.

## Security Considerations

1. **Token Exposure**: The API token is passed in URL parameters, which may be logged in browser history
2. **Token Storage**: The token is stored in browser memory only, not persisted
3. **Clear Function**: Users can clear the token using the "Clear" button
4. **Visibility Toggle**: Token visibility can be toggled for verification

## Troubleshooting

### Common Issues

1. **"Must provide an API key" Error**:
   - Ensure the API token is entered correctly
   - Check that the token matches the Qdrant configuration
   - Try clicking "Test Connection" to verify

2. **"Error: " (Empty Error Message)**:
   - This was caused by wrong HTTP method for collection creation
   - Fixed by changing from POST to PUT method
   - Improved error handling now shows proper error messages

3. **Collections Not Showing**:
   - Collections were not being loaded automatically on page load
   - Fixed by adding `loadCollections()` to page initialization
   - Collections now load automatically when the page loads

4. **Connection Failed**:
   - Verify Qdrant is running: `curl http://localhost:6333/`
   - Check if the API token is correct
   - Ensure no network connectivity issues

5. **Dashboard Link Not Working**:
   - Restart the dashboard service
   - Check dashboard logs for errors
   - Verify the QDRANT_API_KEY environment variable is set

### Debugging Steps

1. **Check Qdrant Status**:
   ```bash
   curl http://localhost:6333/
   ```

2. **Test API with Token**:
   ```bash
   curl -H "api-key: qdrant_api_key" http://localhost:6333/collections
   ```

3. **Test Collection Creation**:
   ```bash
   curl -H "api-key: qdrant_api_key" -X PUT "http://localhost:6333/collections/test" \
     -H "Content-Type: application/json" \
     -d '{"vectors": {"size": 1536, "distance": "Cosine"}}'
   ```

5. **Check Dashboard Configuration**:
   ```bash
   curl http://localhost:8010/api/admin/service-status | jq '.admin_ui_services[] | select(.name == "Qdrant UI")'
   ```

6. **View Qdrant UI Logs**:
   ```bash
   tail -f mep_ainabox/services/qdrant-ui.log
   ```

## Future Improvements

1. **Secure Token Storage**: Implement secure token storage using browser localStorage with encryption
2. **Token Rotation**: Add support for automatic token rotation
3. **Multiple Environments**: Support different API tokens for different environments
4. **Enhanced Security**: Implement token validation and expiration handling
5. **Better Error Handling**: Add more specific error messages for different failure scenarios

## Files Modified

1. `mep_ainabox/services/qdrant-ui/index.html` - Enhanced UI with API token support and fixed collection creation
2. `mep_ainabox/core/dashboard/main.py` - Dashboard integration with API token passing
3. `mep_ainabox/core/test_qdrant_ui_fix.py` - Test script for API token verification
4. `mep_ainabox/core/test_qdrant_collection_fix.py` - Test script for collection creation verification
5. `mep_ainabox/core/test_qdrant_collections_loading.py` - Test script for collections loading verification

## Related Documentation

- [Qdrant UI README](../services/qdrant-ui/README.md)
- [Dashboard Features](DASHBOARD_FEATURES.md)
- [Service Admin UIs](../SERVICE_ADMIN_UIS.md) 