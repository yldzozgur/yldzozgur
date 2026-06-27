---
title: "API keys vs OAuth: which auth model to use for which integration."
description: "The mechanics of API keys and OAuth, when each is appropriate, and how to implement them securely."
pubDate: 2025-08-04
tags: ["DevOps"]
draft: false
---

Every API that requires authentication uses either API keys or OAuth. They look similar on the surface - both involve a token sent with each request - but they have fundamentally different security models and different use cases.

## API keys

An API key is a secret string that identifies and authenticates a client. The client sends it with every request, typically as a header:

```http
GET /api/data HTTP/1.1
Authorization: Bearer sk_live_abc123xyz
```

Or as a query parameter (less secure, as keys appear in server logs and browser history):

```
GET /api/data?api_key=sk_live_abc123xyz
```

The server looks up the key in a database, identifies the caller, and checks their permissions.

API keys are appropriate for **machine-to-machine authentication** where the client is a server under your control. A backend service calling the Stripe API, a CI pipeline calling GitHub's API, a cron job calling your own internal API. The key is stored in environment variables, never exposed to end users.

Implementing API key verification:

```python
def verify_api_key(request):
    key = request.headers.get('Authorization', '').removeprefix('Bearer ')
    if not key:
        return None
    
    # Hash the key before comparing to stored value
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    
    api_key = ApiKey.objects.filter(
        key_hash=key_hash,
        is_active=True
    ).first()
    
    return api_key.owner if api_key else None
```

Store the hash of the key, not the key itself. If the database is breached, raw keys in plaintext give attackers immediate access to every account. Hashed keys require the attacker to have the original key.

## OAuth 2.0

OAuth is an authorization framework designed for **delegated access**: allowing a third-party application to act on behalf of a user, with the user's explicit consent and without the user sharing their password.

The flow:

1. User clicks "Connect with Google" in your app
2. Your app redirects the user to Google's authorization endpoint
3. Google shows a consent screen: "App X wants to read your calendar"
4. User approves
5. Google redirects back to your app with an authorization code
6. Your backend exchanges the code for an access token
7. Your app uses the access token to call Google APIs on the user's behalf

```python
# Step 2: Redirect user to OAuth provider
from urllib.parse import urlencode

def google_oauth_start(request):
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': 'https://yourapp.com/oauth/callback',
        'response_type': 'code',
        'scope': 'https://www.googleapis.com/auth/calendar.readonly',
        'state': generate_csrf_token(),  # Prevent CSRF
    }
    return redirect('https://accounts.google.com/o/oauth2/auth?' + urlencode(params))

# Step 6: Exchange code for token
def google_oauth_callback(request):
    code = request.args['code']
    response = requests.post('https://oauth2.googleapis.com/token', data={
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': 'https://yourapp.com/oauth/callback',
        'grant_type': 'authorization_code',
    })
    tokens = response.json()
    save_tokens(request.user, tokens)
```

## The access token and refresh token

OAuth access tokens are short-lived, typically 1 hour. This limits the damage if a token is leaked. When it expires, the client uses a refresh token (which is longer-lived) to get a new access token without user interaction:

```python
def get_valid_access_token(user):
    token = user.oauth_token
    
    if token.is_expired():
        response = requests.post('https://oauth2.googleapis.com/token', data={
            'refresh_token': token.refresh_token,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'grant_type': 'refresh_token',
        })
        new_tokens = response.json()
        token.access_token = new_tokens['access_token']
        token.expires_at = now() + timedelta(seconds=new_tokens['expires_in'])
        token.save()
    
    return token.access_token
```

## Choosing between them

Use **API keys** when:
- The caller is a server you control
- There is no user involved (background jobs, service-to-service)
- You want simplicity - no token exchange, no expiry management

Use **OAuth** when:
- A third-party app needs to access data on behalf of your users
- You need granular scope-based permissions
- You want users to be able to revoke access without changing their password
- You are building an integration that authenticates with a third-party service as a specific user

The key distinction: API keys identify an application. OAuth tokens represent a user's delegated permission for an application. If a user needs to authorize something, use OAuth. If two servers are talking to each other, use API keys.

## Security baseline for both

For API keys: rotate them on compromise, scope them to minimum permissions, store them only in environment variables or secrets managers, and use separate keys per environment.

For OAuth: always validate the `state` parameter on the callback to prevent CSRF, use PKCE for public clients, store refresh tokens encrypted, and implement token revocation on user logout or account deletion.
