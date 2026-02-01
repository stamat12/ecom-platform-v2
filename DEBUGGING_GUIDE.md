# EAN Retry Mechanism - Debugging Guide

## What Was Added

Comprehensive logging has been added throughout the listing creation and retry mechanism to help identify issues.

## Log Output Levels

### INFO Level (Always Visible)
These logs show major milestones:
- `🚀 STARTING: Create eBay listing for SKU...` - Listing creation begins
- `📂 Loading product JSON for SKU...` - JSON loading
- `✓ Product JSON loaded successfully` - JSON loaded
- `✓ Category ID: {id}` - Category identified
- `📸 Uploading images for SKU...` - Image upload started
- `✓ Uploaded X images` - Images uploaded
- `📤 Sending initial eBay API request for SKU...` - First API call
- `📥 Received response from eBay API` - Response received
- `Response Ack: {ack}, ItemID: {id}` - Response status
- `🔄 Checking if retry is needed for SKU...` - Retry check starting
- `🔁 RETRYING: Attempting retry for SKU...` - Retry attempt
- `📤 Sending retry request to eBay for SKU...` - Retry API call
- `📥 Received retry response from eBay` - Retry response received
- `✅ SUCCESSFUL: Created listing for SKU...` - Success!
- `❌ FAILED: Could not create listing for SKU...` - Final failure
- `✅ RETRY SUCCESSFUL for SKU...` - Retry succeeded
- `❌ Retry also failed for SKU...` - Retry also failed

### DEBUG Level (When Enabled)
These logs show detailed information:
- XML body content (first 500 chars)
- Response content (first 1000 chars)
- Error block counts and details
- EAN extraction process
- Category schema lookups
- Field type checks
- JSON section keys

### ERROR/EXCEPTION Level
- API errors from eBay
- Missing product JSON
- Missing category ID
- Missing images
- Network/connection errors
- Exception stack traces

## How to View Logs

### Option 1: Check the Log File
```bash
cd c:\Users\stame\OneDrive\TRADING_SEGMENT\ecom-platform-v2\backend
type app.log | tail -100  # Last 100 lines
```

### Option 2: Enable Debug Logging
Edit `backend/app/main.py` or the logging config to include DEBUG level:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Option 3: Watch Logs in Real-time (Terminal)
If using uvicorn or another server, logs appear in the terminal running it.

## Debug Flow

When you create a listing, here's what the logs will show:

```
🚀 STARTING: Create eBay listing for SKU JAL00064 at price 29.99€
  ├─ 📂 Loading product JSON for SKU JAL00064
  ├─ ✓ Product JSON loaded successfully
  ├─ ✓ Category ID: 63865
  ├─ 📸 Uploading images for SKU JAL00064
  ├─ ✓ Uploaded 3 images
  ├─ 📤 Sending initial eBay API request for SKU JAL00064
  ├─ 📥 Received response from eBay API (length: 2345 characters)
  ├─ Response Ack: Failure, ItemID: None
  │
  ├─ [IF EAN ERROR]
  ├─ 🔄 Checking if retry is needed for SKU JAL00064
  ├─ 🔁 RETRYING: Attempting retry for SKU JAL00064 with EAN handling...
  ├─ 🔍 Getting EAN value (category_id: 63865)
  ├─ ✓ Priority 3: Using fallback 'Does Not Apply'
  ├─ 📤 Sending retry request to eBay for SKU JAL00064
  ├─ 📥 Received retry response from eBay (length: 3456 characters)
  ├─ Response Ack: Success, ItemID: 123456789
  ├─ ✅ RETRY SUCCESSFUL for SKU JAL00064, ItemID: 123456789
  │
  └─ ✅ SUCCESSFUL: Created listing for SKU JAL00064, ItemID: 123456789
```

## Common Issues & Solutions

### Issue: No response is being shown
**Solution**: Check:
- Is the API endpoint correct? (Check `📤 Sending initial eBay API request`)
- Is the request reaching eBay? (Check `📥 Received response from eBay API`)
- Look at the response Ack value (Failure, Success, or Warning)

### Issue: Retry is not happening
**Solution**: Check:
- Are there actual errors in the response? (Look for error blocks)
- Is the error code 21919301 (EAN error)? (Check debug logs)
- Was `handle_listing_error` called? (Look for `🔄 Checking if retry is needed`)

### Issue: Retry is happening but still failing
**Solution**: Check:
- What EAN value was used? (Look for `✓ Priority X:` messages)
- What was the retry response? (Check `📥 Received retry response from eBay`)
- Did the XML change? (Compare XML preview in logs)

### Issue: Exception is thrown
**Solution**: Look for:
- `💥 EXCEPTION in create_listing` messages
- Stack trace with `exc_info=True`
- The exception type and message

## Key Information to Provide When Asking for Help

1. The complete log output from listing creation attempt
2. The SKU that failed
3. The exact error code from eBay (e.g., 21919301)
4. Whether retry happened or not
5. If retry happened, what was the retry result?

## Example Complete Log

```
=================================================================================
🚀 STARTING: Create eBay listing for SKU JAL00064 at price 29.99€
=================================================================================
Parameters: condition_id=None, schedule_days=0, quantity=1, ebay_sku=None
📂 Loading product JSON for SKU JAL00064
✓ Product JSON loaded successfully
✓ Category ID: 63865
✓ Uploaded 3 images
📤 Sending initial eBay API request for SKU JAL00064
📥 Received response from eBay API (length: 3245 characters)
Response Ack: Failure, ItemID: None
Parsed 0 warnings and 1 errors
🔄 Checking if retry is needed for SKU JAL00064
🔁 RETRYING: Attempting retry for SKU JAL00064 with EAN handling...
🔍 Getting EAN value (category_id: 63865)
✓ Priority 3: Using fallback 'Does Not Apply'
📤 Sending retry request to eBay for SKU JAL00064
📥 Received retry response from eBay (length: 2567 characters)
Response Ack: Success, ItemID: 153847292
✅ RETRY SUCCESSFUL for SKU JAL00064, ItemID: 153847292
✅ SUCCESSFUL: Created listing for SKU JAL00064, ItemID: 153847292
=================================================================================
```

## Enable/Disable Debug Logs Temporarily

### In Python Code
```python
import logging
logging.getLogger("app.services.ebay_listing").setLevel(logging.DEBUG)
logging.getLogger("app.services.ebay_listing_retry").setLevel(logging.DEBUG)
```

### Via Environment Variable
```bash
LOGLEVEL=DEBUG python main.py
```

### Via Logging Config File
Create `.logging.yaml` with appropriate level settings.

---

**The implementation now provides full visibility into:**
1. ✅ When listing creation starts
2. ✅ What data is being used (product JSON, category, etc.)
3. ✅ What requests are sent to eBay (with content preview)
4. ✅ What responses come back from eBay
5. ✅ Whether/when EAN retry happens
6. ✅ What EAN value is used and why
7. ✅ Whether retry succeeds or fails
8. ✅ Any exceptions that occur

You can now debug any issues by reading the logs!
