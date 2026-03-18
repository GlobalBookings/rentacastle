import { google } from 'googleapis';

let _oauth2Client = null;

export function getOAuth2Client() {
  if (_oauth2Client) return _oauth2Client;

  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  const refreshToken = process.env.GOOGLE_REFRESH_TOKEN;

  if (!clientId || !clientSecret) {
    throw new Error('Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in .env');
  }

  _oauth2Client = new google.auth.OAuth2(clientId, clientSecret, 'http://localhost:3000/oauth2callback');

  if (refreshToken) {
    _oauth2Client.setCredentials({ refresh_token: refreshToken });
  }

  return _oauth2Client;
}

export async function getAccessToken() {
  const client = getOAuth2Client();
  const { token } = await client.getAccessToken();
  return token;
}
