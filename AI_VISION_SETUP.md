# AI Vision Setup Guide

VisionGuardian now supports **AI-powered vision recognition** using cloud services like OpenAI GPT-4 Vision and Google Cloud Vision. This provides significantly better recognition accuracy compared to the offline models.

## Why Use AI Vision?

**AI Vision provides:**
- Comprehensive scene understanding
- Accurate object recognition (thousands of objects, not just 80)
- Superior text reading (handles handwriting, multiple languages, skewed text)
- Detailed descriptions tailored for visually impaired users
- Context-aware analysis

**Comparison:**

| Feature | Local Models | AI Vision |
|---------|-------------|-----------|
| Objects Recognized | ~80 (COCO) | Thousands |
| Scene Description | Basic (brightness, edges) | Detailed, contextual |
| Text Recognition | Basic (Tesseract) | Advanced (handwriting, angles) |
| Accuracy | Medium | High |
| Internet Required | No | Yes |
| Cost | Free | Pay per API call |

---

## Option 1: OpenAI GPT-4 Vision (Recommended)

### Step 1: Get OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com)
2. Sign up or log in
3. Go to [API Keys](https://platform.openai.com/api-keys)
4. Click "Create new secret key"
5. Give it a name (e.g., "VisionGuardian")
6. Copy the API key (starts with `sk-...`)

**Important:** Keep your API key secure! Never share it publicly.

### Step 2: Configure VisionGuardian

On your Raspberry Pi, edit the configuration file:

```bash
cd ~/Vision_Guardian/blind-assistant
nano config/settings.yaml
```

Find the `ai_vision` section and update it:

```yaml
ai_vision:
  enabled: true  # Change from false to true
  primary_service: "openai"
  openai_api_key: "sk-your-actual-api-key-here"  # Paste your API key
  detail_level: "high"
  fallback_to_local: true
  min_interval_seconds: 2
```

Save and exit (Ctrl+X, Y, Enter)

### Step 3: Install Dependencies

```bash
cd ~/Vision_Guardian/blind-assistant
source venv/bin/activate
pip install openai>=1.3.0
```

### Step 4: Test AI Vision

```bash
python3 src/ai_vision.py
```

This will test the API connection and analyze a test image.

### Pricing

OpenAI GPT-4 Vision pricing (as of 2025):
- **$0.01 per image** (high detail)
- **$0.00265 per image** (low detail)

Example usage:
- 100 scene descriptions per day = ~$1/day with high detail
- Set `detail_level: "medium"` in config to reduce costs
- Increase `min_interval_seconds` to limit API calls

---

## Option 2: Google Cloud Vision

### Step 1: Set Up Google Cloud

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable the **Cloud Vision API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Cloud Vision API"
   - Click "Enable"

### Step 2: Create Service Account

1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Name it "visionguardian"
4. Grant role: "Cloud Vision API User"
5. Click "Create Key"
6. Choose "JSON" format
7. Download the credentials file

### Step 3: Transfer Credentials to Raspberry Pi

Transfer the downloaded JSON file to your Raspberry Pi:

```bash
# On your computer
scp /path/to/credentials.json pi@raspberrypi:~/Vision_Guardian/blind-assistant/config/
```

### Step 4: Configure VisionGuardian

```bash
nano config/settings.yaml
```

Update the AI vision settings:

```yaml
ai_vision:
  enabled: true
  primary_service: "google"
  google_credentials_path: "config/credentials.json"
  detail_level: "high"
  fallback_to_local: true
```

### Step 5: Install Dependencies

```bash
source venv/bin/activate
pip install google-cloud-vision>=3.4.0
```

### Pricing

Google Cloud Vision pricing (as of 2025):
- First 1,000 requests/month: **FREE**
- After that: **$1.50 per 1,000 images**

Much cheaper than OpenAI for high usage!

---

## Using AI Vision

Once configured, AI Vision automatically activates when you:

1. **Say "What do you see?"** - Uses AI for comprehensive scene description
2. **Say "Read text"** - Uses AI for superior text recognition
3. Ask any visual question - AI provides detailed, helpful answers

### Voice Commands

All existing commands now use AI Vision when enabled:

- **"Hey Guardian, what do you see?"** - Detailed scene analysis
- **"Hey Guardian, read text"** - Read any visible text
- **"Hey Guardian, describe the scene"** - Comprehensive description
- **"Hey Guardian, who is here?"** - Detect people (with facial recognition)

### Example Output

**Without AI Vision:**
> "Moderate lighting. You appear to be indoors. Moderate scene complexity."

**With AI Vision:**
> "You're in a modern kitchen with white cabinets and granite countertops. There's a stainless steel refrigerator on your left, a sink directly ahead with a window above it showing a garden view. On the counter, I see a red kettle, a toaster, and some fruit in a bowl. The room is well-lit with natural daylight coming through the window. No obstacles in your immediate path."

---

## Troubleshooting

### "AI Vision disabled" Message

**Check:**
1. Is `enabled: true` in config?
2. Is your API key correct?
3. Is internet connected?
4. Did you install dependencies?

Test connection:
```bash
source venv/bin/activate
python3 -c "import openai; print('OpenAI installed')"
# or
python3 -c "from google.cloud import vision; print('Google Vision installed')"
```

### "API Error" or Timeout

**Solutions:**
- Check internet connection: `ping 8.8.8.8`
- Increase timeout in config: `timeout_seconds: 20`
- Check API quotas/billing in your dashboard

### "Rate Limit Exceeded"

OpenAI has rate limits. Solutions:
- Increase `min_interval_seconds: 5` (wait longer between calls)
- Upgrade to higher tier API plan
- Switch to Google Vision (higher free tier)

### High API Costs

**Reduce costs:**
```yaml
ai_vision:
  detail_level: "medium"  # Use medium instead of high
  min_interval_seconds: 5  # Increase interval
```

- Use AI Vision only on demand (don't enable continuous monitoring)
- Keep `fallback_to_local: true` to use offline models when possible

---

## Best Practices

### 1. Optimize API Usage

```yaml
ai_vision:
  min_interval_seconds: 3  # Don't query too frequently
  fallback_to_local: true  # Use offline models when AI fails
```

### 2. Choose the Right Service

- **OpenAI GPT-4 Vision**: Best descriptions, understands context
- **Google Cloud Vision**: Cheaper, faster, good for object/text detection

### 3. Monitor Usage

**OpenAI:** Check usage at https://platform.openai.com/usage

**Google Cloud:** Check at https://console.cloud.google.com/billing

### 4. Security

- Never commit API keys to Git
- Keep credentials file secure (`chmod 600 config/credentials.json`)
- Rotate keys periodically
- Set spending limits in API dashboard

---

## Comparing Services

| Feature | OpenAI GPT-4 Vision | Google Cloud Vision |
|---------|-------------------|---------------------|
| Scene Understanding | Excellent | Good |
| Object Detection | Excellent | Excellent |
| Text Recognition | Excellent | Excellent |
| Context Awareness | Superior | Basic |
| Descriptions | Natural, detailed | Technical, precise |
| Cost | Higher ($0.01/image) | Lower (1000 free/month) |
| Speed | 2-5 seconds | 1-2 seconds |
| Free Tier | $5 credit for new users | 1000 images/month |

**Recommendation:**
- Start with Google Vision (free tier)
- If you need better descriptions, switch to OpenAI
- Or use Google as primary, OpenAI as fallback

---

## Hybrid Setup (Best of Both)

Use both services for maximum reliability:

```yaml
ai_vision:
  enabled: true
  primary_service: "google"  # Fast, cheaper
  openai_api_key: "sk-..."    # Fallback for complex scenes
  google_credentials_path: "config/credentials.json"
  fallback_to_local: true
```

This configuration:
1. Uses Google Vision by default (fast, cheap)
2. Falls back to OpenAI if Google fails
3. Falls back to offline models if both fail

---

## Complete Example Setup

### Full config/settings.yaml entry:

```yaml
# AI Vision Settings (Cloud-based, requires internet and API key)
ai_vision:
  enabled: true  # Enable AI-powered vision
  primary_service: "openai"  # or "google"
  openai_api_key: "sk-proj-abcdefghijklmnopqrstuvwxyz..."
  google_credentials_path: ""  # Leave empty if not using Google
  detail_level: "high"  # low, medium, high (affects cost)
  fallback_to_local: true  # Use offline models if API fails
  min_interval_seconds: 2  # Minimum time between API calls
  max_retries: 2
  timeout_seconds: 10
```

---

## Testing Your Setup

### Quick Test

```bash
cd ~/Vision_Guardian/blind-assistant
source venv/bin/activate
python3 src/ai_vision.py
```

### Full System Test

```bash
python3 src/main.py
```

Then try voice commands:
- "Hey Guardian, what do you see?"
- "Hey Guardian, read text"

---

## FAQ

**Q: Do I need both OpenAI AND Google?**
A: No, choose one. Google is cheaper, OpenAI gives better descriptions.

**Q: Will it work without internet?**
A: Yes! It automatically falls back to offline models when internet is unavailable.

**Q: How much will it cost?**
A: Google: First 1000/month FREE. OpenAI: ~$1-3/day with heavy use.

**Q: Can I use it for free?**
A: Yes, use Google Cloud Vision free tier (1000 images/month).

**Q: Which is more accurate?**
A: OpenAI GPT-4 Vision is more accurate for complex scenes. Google is faster for simple tasks.

**Q: How do I switch between services?**
A: Change `primary_service: "openai"` to `primary_service: "google"` in config.

---

## Support

If you encounter issues:

1. Check logs: `cat logs/visionguardian.log`
2. Test API connection separately
3. Verify API keys are correct
4. Check internet connectivity
5. Review API dashboard for errors

---

## Next Steps

After setting up AI Vision:

1. Test with different scenes
2. Adjust `detail_level` for your needs
3. Monitor API usage and costs
4. Fine-tune `min_interval_seconds` for your workflow
5. Add known faces for better recognition

**Enjoy superior AI-powered vision recognition!**
