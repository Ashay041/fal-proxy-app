# [FAL AI Proxy Application - Documentation](https://distinct-driver-eb0.notion.site/fal-proxy-app-documentation-2cb5dcb41f3c80dc9a0eddc91b0e8c5a)
## Table of context

**1. Introduction**

**2. Setup and Running Locally**

* Prerequisites
* Environment Configuration
* Running Locally

**3. Architecture**

* Tech Stack
* Request Flow (IMPORTANT)

**4. High-Level Design Trade-offs (IMPORTANT)**

**5. REST APIs**

**6. System Design Principles**

* Single Responsibility Principle (SRP)
* DRY (Don't Repeat Yourself)
* Separation of Concerns
* Validation Checks and Resilience
* Fail Fast Approach
* Idempotency

**7. Future Improvements**

**8. Appendix: Requirements Gathering**

---

## 1. Introduction

This is a web application that makes it easy to transform images using AI. You upload a photo, describe what changes you want, and get back AI-generated results - all without worrying about the technical complexity behind the scenes.

### Try it out:

**Live Demo:** [https://fal-proxy-app.onrender.com](https://fal-proxy-app.onrender.com)

 **Github** : [https://github.com/Ashay041/fal-proxy-app](https://github.com/Ashay041/fal-proxy-app)

> Heads up: The app is on Render's free tier, so the first visit might take about a minute to wake up. After that, it's fast.

### Main Features

* **Two ways to provide images:** Paste a URL or upload a file directly
* **Smart caching:** If someone already requested the same image with the same prompt, results come back instantly from cache instead of calling the expensive AI API again
* **Handles failures gracefully:** If the AI service is temporarily down or slow, the app automatically retries instead of just failing
* **Stores everything reliably:** All images (yours and generated ones) are saved to Supabase cloud storage, so they don't disappear
* **Three AI model options:** Choose between base quality, max quality, or development versions

### What's Under the Hood

Built with FastAPI, talks to FAL AI for the actual image generation, uses Redis to cache results, stores images on Supabase, and runs on Render's cloud platform. GitHub Actions automatically tests and deploys new code.

---

## 2. Setup and Running Locally

### Prerequisites (optional as I have shared my creds to .env file)

* Python 3.8+ and docker
* Upstash Redis account
* Supabase account
* FAL AI API key
* Neon DB account (optional, for persistent storage)

### Environment Configuration

Create a `.env` file in the root directory with the following credentials:

Ask me at koradiaashay@gmail.com for my .env file if you wish to try running locally

```bash
# FAL AI Configuration
FAL_KEY=""
# Supabase Configuration
SUPABASE_URL=""
SUPABASE_KEY=""
# Neon DB Configuration (optional)
DATABASE_URL=""
# Redis Configuration (Upstash)
REDIS_URL=""
```

### Running Locally

1. Make the run script executable:

```bash
chmod +x run.sh
```

1. Execute the application:

```bash
./run.sh
```

The application will start on `http://localhost:8000`

---

## 3. Architecture

### 3.1 Tech Stack

| Technology               | Purpose                                                            |
| ------------------------ | ------------------------------------------------------------------ |
| **FastAPI**        | Async web framework for building REST APIs                         |
| **Supabase**       | Cloud storage for uploaded and generated images                    |
| **Upstash Redis**  | Serverless cache layer for reducing redundant API calls            |
| **FAL AI**         | AI model provider for image generation (Kontext models)            |
| **Neon DB**        | Serverless PostgreSQL database for metadata storage                |
| **HTTPX**          | Async HTTP client for downloading images and calling external APIs |
| **Tenacity**       | Retry logic library for handling API failures                      |
| **Pytest**         | Testing framework for unit tests                                   |
| **GitHub Actions** | CI/CD pipeline for automated testing                               |
| **Render**         | Cloud platform for deployment and hosting                          |

### 3.2 Request Flow (IMPORTANT)

[Backend Flow](https://drive.google.com/file/d/1ZWrLxGvdsevy7e_AH2y2YbCTyVWgEJk9/view)

---

## 4. High-Level Design Trade-offs (IMPORTANT)

### 4.1 Asynchronous Architecture

1. **Question:** Should we use synchronous (blocking) code or asynchronous (non-blocking) code for handling requests?
2. **Decision taken:** We chose **asynchronous programming** with `async`/`await` throughout the entire application.
3. **Reason:** When a user uploads an image, the server needs to download it, talk to external APIs like FAL AI and Supabase, and wait for responses. With synchronous code, each request would **block a thread** while waiting. With async code, while one request is waiting for FAL AI to respond, the server can handle other users' requests.1 This means we can serve many more users at the same time  **without needing more hardware** .
4. **Tradeoffs:** The code is a bit harder to write and understand because we have to use `async` and `await` keywords everywhere. However, the performance gains are massive - we can handle **1000+ users** instead of just 30-40 users with the same resources.

### 4.2 Unified Processing Function

1. **Question:** Should we write separate functions for each model endpoint (`/kontext`, `/kontext/max`, `/kontext/dev`), or use one shared function?
2. **Decision taken:** We use a **single function** called `process_kontext_request()` that handles all three endpoints.
3. **Reason:** All three endpoints do almost the same thing: take an image, validate it, upload it, call FAL AI, and return results. If we wrote separate functions, we'd be copying and pasting the same code three times. When we fix a bug or add a feature, we'd have to update it in three places. With one shared function, we  **fix it once and all endpoints benefit** .
4. **Tradeoffs:** The single function is slightly more complex because it needs to handle different parameters for different endpoints. But this complexity is worth it because **maintaining one function is much easier** than maintaining three identical copies.

### 4.3 Magic Bytes for Image Type Detection

1. **Question:** How should we verify that an uploaded file is actually a JPEG or PNG image and not something malicious?
2. **Decision taken:** We read the **first few bytes of the file** (called "magic bytes") to detect the actual file type, instead of trusting the file extension or HTTP headers.
3. **Reason:** A malicious user could rename a virus from "virus.exe" to "image.jpg" and try to upload it. If we only check the filename, we'd think it's an image. But every file format has a **unique signature** in its first few bytes - JPEGs always start with `\\xff\\xd8`, and PNGs always start with `\\x89PNG`. By reading these bytes, we know for certain what the file really is, regardless of what the user named it.
4. **Tradeoffs:** We have to read the file into memory to check the magic bytes, which uses a tiny bit more processing power. But the **security benefit is huge** - we can't be fooled by fake file extensions or manipulated headers.

### 4.4 Chunked Image Downloads

1. **Question:** When downloading an image from a URL, should we download the entire file at once, or download it in small pieces?
2. **Decision taken:** We download images in **small chunks** (8KB at a time) and check the total size after each chunk.
3. **Reason:** Imagine a malicious user provides a URL to a 10GB file. If we tried to download the whole thing at once, our server would  **run out of memory and crash** . By downloading in chunks and keeping track of the total size, we can stop immediately when we hit our 100MB limit. We only downloaded 100MB instead of 10GB,  **saving bandwidth and protecting our server** .
4. **Tradeoffs:** Downloading in chunks is slightly slower than downloading all at once (maybe 100-200ms difference). But it **prevents our server from being crashed** by extremely large files, which is far more important.

### 4.5 Retry Logic with Tenacity

1. **Question:** When an external API call fails (like calling FAL AI or Supabase), should we give up immediately or try again?
2. **Decision taken:** We automatically retry failed requests up to 3 times with  **exponential backoff** . For FAL AI calls, delays increase from 2 seconds to a maximum of 30 seconds. For image downloads, delays start at 1 second with a maximum of 10 seconds. We **don't retry** on `ValueError` exceptions (client errors).
3. **Reason:** Sometimes APIs fail temporarily due to network hiccups, rate limiting, or server overload.2 If we give up immediately, users see errors even though the API might work fine a few seconds later. By retrying automatically with increasing delays, we handle these temporary failures  **without bothering the user** . The exponential backoff prevents us from  **hammering a struggling API** . We skip retries for `ValueError` because those indicate bad user input that won't be fixed by retrying.
4. **Tradeoffs:** If an API is truly down, users have to **wait longer** to see an error message (up to 60+ seconds for all retries with backoff). But in practice, most failures are temporary, so retrying dramatically **improves success rates** and user experience.

### 4.6 Dual Input Method Support

1. **Question:** Should users only be able to provide image URLs, or should we also let them upload files directly?
2. **Decision taken:** We support **both methods** - users can paste a URL or drag-and-drop a file from their computer.
3. **Reason:** Different users have different needs. Some have images already hosted online (easy to share a URL). Others have images on their laptop (easier to drag-and-drop). By supporting both, we don't force users to upload their image somewhere else first just to get a URL. After we get the image (either downloaded from URL or uploaded), the  **rest of the code is identical** .
4. **Tradeoffs:** We need extra validation logic to ensure users provide **exactly one input method** (not both, not neither). But the improved user experience is worth this small complexity.

### 4.7 Redis Caching with SHA256 Hashing

1. **Question:** Should we process every request fresh, or save results so identical requests can be answered instantly?
2. **Decision taken:** We cache results in Redis for  **1 hour** . The cache key is a **SHA256 hash** of the image content plus all the settings.
3. **Reason:** If a user uploads the same image with the same prompt twice within an hour, why call FAL AI again and wait 5 seconds? We can return the cached result in milliseconds. The cache key is based on the **actual image content** (not the filename), so even if someone uploads "cat.jpg" via URL and someone else uploads the same cat photo from their computer, they get the same cached result. This **saves money on API calls** and makes the app feel instant for repeat requests. We chose 1 hour because it balances cost savings with ensuring users can get fresh results if they wait a bit.
4. **Tradeoffs:** We need to run Redis, which adds infrastructure complexity. The 1-hour TTL means very frequent users might want fresher results but get cached ones. However, the benefits are significant - we reduce FAL AI costs and make repeat requests within the hour **1000x faster** (milliseconds instead of seconds).

### 4.8 Base64 Encoding for File Uploads

1. **Question:** When users upload files, should we use standard file upload format (multipart/form-data) or convert files to base64 text?
2. **Decision taken:** We convert files to **base64 in the browser** and send them as JSON.
3. **Reason:** Our API is designed around clean JSON requests using Pydantic models. Multipart/form-data would require special handling code and a different code path from URL inputs. With base64, both URL and file inputs go through the **exact same JSON API** - just one field (`image_url` or `image_data`) is filled. This keeps the code simple and maintainable.
4. **Tradeoffs:** Base64 encoding makes files about **33% larger** (a 3MB image becomes 4MB) But for our 10MB upload limit, this is fine, and the cleaner code is worth the slightly larger uploads.

### 4.9 Frontend and Backend Validation

1. **Question:** Should we validate file size and type only in the browser, only on the server, or both?
2. **Decision taken:** We validate in **both places** - browser checks first, then server checks again.
3. **Reason:** Frontend validation gives instant feedback - if you try to upload a 50MB file, you see an error immediately without waiting for the upload. But a malicious user could **disable JavaScript** and bypass frontend checks. So the backend validates again to prevent abuse.
4. **Tradeoffs:** We have to write and maintain the validation logic twice (once in JavaScript, once in Python). But this is a **fundamental security practice** - we can't skip backend validation.

### 4.10 CI/CD Pipeline

1. **Question:** Should we manually test and deploy changes, or automate the entire process?
2. **Decision taken:** **GitHub Actions** automatically runs tests on every pull request (CI), and **Render** automatically deploys when we merge to the main branch (CD).
3. **Reason:** Humans forget things. Maybe you forget to run tests before deploying and accidentally break production. With automation, **every single change is tested** before it can be merged. Tests must pass or the code can't go live. When we merge, deployment happens automatically and consistently - no manual steps to forget.
4. **Tradeoffs:** Setting up CI/CD takes time initially and needs maintenance. But it **prevents bugs from reaching users** and gives us confidence to deploy multiple times per day without fear.

### 4.11 Persistent Storage

1. **Question:** Should we automatically delete uploaded images after some time, or keep them forever?
2. **Decision taken:** We keep all images in Supabase **indefinitely** (no automatic cleanup).
3. **Reason:** During the requirements phase, we asked if storage cleanup was needed and were told it **wasn't a concern** to begin with.
4. **Tradeoffs:** Storage grows over time without cleanup. But Supabase is cheap, and this was an explicit non-concern during planning. We can always **add cleanup later** if needed.

### 4.12 Parameter Filtering

1. **Question:** Should we send all possible parameters to every FAL AI endpoint, or only the ones each endpoint actually supports?
2. **Decision taken:** We **filter parameters** based on which Kontext variant is being called. We have three variants: `/kontext`, `/kontext/max`, and `/kontext/dev` - each accepts a different subset of parameters. We maintain a configuration that **whitelists allowed parameters** per endpoint.
3. **Reason:** Even though all three endpoints use the Kontext model family, they have different capabilities and accept different parameters. For example, one variant might support certain advanced settings while another doesn't. If we send unsupported parameters, the FAL API might  **throw errors or behave unexpectedly** . By filtering to only send parameters that each variant accepts, we prevent API errors and keep the system working reliably. This also makes it easy to add new Kontext variants in the future - just add their parameter whitelist to the configuration.
4. **Tradeoffs:** We have to maintain a **configuration mapping** of which parameters each endpoint variant accepts. This requires updating the config when FAL AI changes their API. But this prevents runtime API errors and makes the system more robust and maintainable.

---

## 5. REST APIs

### Base URL

* **Production:** `https://fal-proxy-app.onrender.com`
* **Local:** `http://localhost:8000`

### Endpoints

| Endpoint         | Method | Description                                                         |
| ---------------- | ------ | ------------------------------------------------------------------- |
| `/kontext`     | POST   | Generate images using FAL Kontext base model                        |
| `/kontext/max` | POST   | Generate images using FAL Kontext Max variant (enhanced quality)    |
| `/kontext/dev` | POST   | Generate images using FAL Kontext Dev variant (development/testing) |
| `/health`      | GET    | Health check endpoint - returns server status                       |
| `/`            | GET    | Serves the web application UI                                       |

### Request Format

**Content-Type:** `application/json`

**Note:** Exactly one of `image_url` OR `image_data` must be provided (not both, not neither).

```json
{
  "image_url": "<https://example.com/image.jpg>",  // Option 1: Image URL
  "image_data": "base64_encoded_image_string",   // Option 2: Base64 file upload

  "prompt": "your generation prompt",            // Required

  // Optional parameters (not all variants support all parameters)
  "seed": 42,
  "guidance_scale": 7.5,
  "num_images": 1,
  "output_format": "jpeg",
  "enhance_prompt": true,
  "safety_tolerance": 2,
  "aspect_ratio": "16:9",
  "num_inference_steps": 50,
  "enable_safety_checker": true,
  "acceleration": "auto",
  "resolution_mode": "high"
}

```

### Example Requests

**1. Using Image URL:**

```json
{
  "image_url": "<https://example.com/cat.jpg>",
  "prompt": "transform into a cartoon style"
}

```

**2. Using File Upload (Base64):**

```json
{
  "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAUA...",
  "prompt": "make it look like a painting",
  "num_images": 2,
  "output_format": "png"
}

```

**3. Using Advanced Options:**

```json
{
  "image_url": "<https://example.com/portrait.jpg>",
  "prompt": "professional headshot style",
  "seed": 12345,
  "guidance_scale": 8.0,
  "num_inference_steps": 50,
  "enable_safety_checker": true,
  "aspect_ratio": "1:1"
}

```

### Response Format

**Success Response (200 OK):**

```json
{
  "images": [
    {
      "url": "<https://your-supabase-url.supabase.co/storage/v1/object/public/bucket/generated-image.jpg>",
      "width": 1024,
      "height": 1024
    }
  ],
  "prompt": "enhanced version of your prompt with additional details"
}

```

**Response Fields:**

* `images`: Array of generated images stored in Supabase
  * `url`: Public Supabase storage URL for the generated image
  * `width`: Image width in pixels (if available from FAL API)
  * `height`: Image height in pixels (if available from FAL API)
* `prompt`: The final prompt used by FAL API (may be enhanced if `enhance_prompt: true`)

### Error Response

### Status Codes

| Code | Meaning               | Common Causes                                                        |
| ---- | --------------------- | -------------------------------------------------------------------- |
| 200  | Success               | Request processed successfully                                       |
| 400  | Bad Request           | Invalid input, missing required fields, file too large, wrong format |
| 500  | Internal Server Error | FAL API failure, Supabase storage failure, network issues            |
| 503  | Service Unavailable   | FAL API is down or experiencing issues                               |

### Validation Rules

**Image URL Input:**

* Must be a valid HTTP/HTTPS URL
* Image must be JPEG or PNG format (validated using magic bytes)
* Maximum size: 100MB
* Downloaded in chunks with early termination if size exceeded

**Image Upload Input:**

* Must be base64-encoded string
* Must decode to valid JPEG or PNG (validated using magic bytes)
* Maximum size: 10MB (before base64 encoding)
* Automatically uploaded to Supabase storage

**Common Rules:**

* Exactly one of `image_url` or `image_data` required
* `prompt` field is always required
* All optional parameters are filtered based on endpoint variant capabilities

### cURL Examples

**Basic request with URL:**

```bash
curl -X POST <https://fal-proxy-app.onrender.com/kontext> \\
  -H "Content-Type: application/json" \\
  -d '{
    "image_url": "<https://example.com/image.jpg>",
    "prompt": "change to artistic watercolor style"
  }'

```

**Request with advanced options:**

```bash
curl -X POST <https://fal-proxy-app.onrender.com/kontext/max> \\
  -H "Content-Type: application/json" \\
  -d '{
    "image_url": "<https://example.com/photo.jpg>",
    "prompt": "cyberpunk neon style",
    "num_images": 2,
    "seed": 42,
    "guidance_scale": 7.5
  }'

```

---

## 6. System Design Principles

### 6.1 Single Responsibility Principle (SRP)

Each module has a clear, focused purpose:

* `main.py` - API endpoints and request orchestration
* `fal_service.py` - FAL AI API integration
* `image_service.py` - Image validation and processing
* `cache_service.py` - Caching logic
* `storage_service.py` - Supabase storage operations

### 6.2 DRY (Don't Repeat Yourself)

* Unified processing function for all endpoints
* Reusable validation functions
* Common error handling patterns

### 6.3 Separation of Concerns

* Frontend handles UX and basic validation
* Backend handles security, business logic, and external APIs
* Cache layer handles performance optimization

### 6.4 Validation checks and resilience

* Multiple validation layers (frontend + backend)
* Magic bytes validation for file types
* Size limits enforced at multiple stages
* Retry logic for resilience

### 6.5 Fail Fast approach

* Input validation before expensive operations
* Early termination of oversized downloads
* Cache check before processing

### 6.6 Idempotency

* Same request produces same result
* Caching ensures consistency

---

## **7. Future Improvements**

**I shared my app to my family and friends to get real feedback**

The current implementation works well. There is a reliable proxy, smart caching, dual input support. But as usage grows, three questions emerge:
 **"How do we know when things break?"** ,  **"How do we handle more traffic?"** , and **"What do users actually need?"**

---

### 7.1 Observability: Know What's Happening

**The Problem:** Right now, we only know something's wrong when a user complains. We don't know cache hit rates, response times, or which endpoints are popular. When things slow down, we can't tell if it's FAL AI, Supabase, or our code.

**Start Simple:**

1. **Replace `print()` with structured logging** - Free, immediate value
2. **Track key metrics** - Cache hit rate, response time, error rate by endpoint
3. **Use Render's built-in metrics** - Should avoid over-engineering first

**Success means:** Able to answer "Why was it slow yesterday?" or "Should we upgrade Redis?"

---

### 7.2 Scaling without Over-Engineering

**Reality Check:** Render's free tier handles hundreds of users fine. Kubernetes is overkill until thousands of concurrent requests. Kubernetes is very costly at scale

**Incremental Path:**

* **Phase 1 (1K-5K users):** Render $7/month tier + paid Redis (~$20/month total)
* **Phase 2 (10K+ users):** Multiple instances + load balancer (~$100/month)
* **Phase 3 (100K+ users):** Consider Kubernetes (but probably not needed)

---

### 7.3 User Experience

**Prioritized by Impact:**

1. **Before/after comparison slider**
   * Users currently open two tabs to compare
2. **Loading progress indicator**
   * 5-10 seconds of silence feels broken
3. **Basic history with localStorage**
   * Users can't find previous images
4. Download button

**Skip These:**

* Parameter presets (nobody changes defaults)
* Share buttons (URLs already work)

---

### 7.4 Cost Optimization

**Insight:** FAL API calls are the biggest cost

**High ROI:** Implement auto clean up for the image store

---

### 7.5 Developer Experience

1. **Better error messages** - "[fal.ai](http://fal.ai) timeout (30s)" not "had a problem"
2. **Single config file** - All settings in one place
3. **Integration tests** - Catch breaking changes early

**Ask:** "If I handed this to another developer, what would confuse them?"

---

### 7.6 What NOT to Build

**Don't build until users ask:**

* User auth
* Rate limiting
* Microservices

**Principle:** Build when needed, not what sounds cool.

---

**Developing Philosophy:** Make it work. Make it observable. Make it fast. In that order.

---

## 8. Appendix: Requirements Gathering

During the planning phase, the following technical questions were asked for clarification:

**High Priority (Architecture Decisions):**

1. **Concurrent users & scalability:** What's the expected concurrent user load? This determines whether I should use synchronous blocking (suitable for ~30-40 concurrent users with FastAPI's default thread pool) or async/queue-based architecture (1000+ users).
2. **Endpoint behavior:** Should all three endpoints (`/kontext`, `/kontext/max`, `/kontext/dev`) have identical proxy behavior, or do they have different requirements? (e.g. Same rate limiting? or Same timeout settings?)
3. **Response latency:** Is there any response time requirement? (for e.g. must complete within 10 seconds)? Are there different timeout expectations for the three kontext variants? (e.g., should `/kontext/max` have a longer timeout since it may take more processing time?

**Medium Priority (Storage & auth decisions):**

1. **Image Storage policy:** Should I implement automatic cleanup of uploaded images, or is persistent storage expected? Without cleanup, storage will grow unbounded and with immediate cleanup, we lose debugging capability. So it is a tradeoff.
2. **Authentication:** Does the proxy need authentication, or can it remain open for this implementation?

**Lower Priority (Input Validation):**

1. **Image constraints:** What's the maximum accepted image size, and which formats should we support? Should I enforce limits?
2. **Image modifications** : Should the proxy perform any image transformations considering user requirements? (e.g. fixed output resolution is required to fit in a UI window? or Image compression before storing)

Answers received:

1. Either way is fine
2. Same
3. No response latency requirement.
4. Not a concern
5. It can just use your fal API key
6. 100 mb
7. Nope
