// api/contact.js - Vercel Serverless Function
// Reçoit les données du formulaire de contact, envoie un email via Resend
// et enregistre la soumission dans la Google Sheet via Apps Script Web App.
//
// Variables d'environnement requises (Vercel Dashboard > Settings > Environment Variables) :
//   RESEND_API_KEY         — clé API Resend (https://resend.com)
//   CONTACT_FROM_EMAIL     — adresse expéditrice vérifiée sur Resend (ex: contact@frenchnamesaustralia.com)
//   CONTACT_TO_EMAIL       — destinataire
//   GOOGLE_SHEET_WEBHOOK   — URL du Google Apps Script Web App déployé sur la feuille

const ALLOWED_ORIGINS = new Set([
  'https://french-names-australia.vercel.app',
  'https://www.frenchplacenames.au',
  'https://frenchplacenames.au',
  'https://www.frenchplacenames.com',
  'https://frenchplacenames.com',
]);

const RATE_LIMIT_WINDOW_MS = 15 * 60 * 1000;
const RATE_LIMIT_MAX_SUBMISSIONS = 5;
const rateLimitStore = new Map();

function normalizeOrigin(value) {
  if (!value) return null;
  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

function getAllowedRequestOrigin(req) {
  const origin = normalizeOrigin(req.headers.origin);
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    return origin;
  }

  const refererOrigin = normalizeOrigin(req.headers.referer);
  if (refererOrigin && ALLOWED_ORIGINS.has(refererOrigin)) {
    return refererOrigin;
  }

  return null;
}

function getClientIp(req) {
  const forwardedFor = req.headers['x-forwarded-for'];
  if (typeof forwardedFor === 'string' && forwardedFor.trim()) {
    return forwardedFor.split(',')[0].trim();
  }
  return req.socket?.remoteAddress || 'unknown';
}

function consumeRateLimit(ip) {
  const now = Date.now();

  for (const [key, timestamps] of rateLimitStore.entries()) {
    const recent = timestamps.filter((ts) => now - ts < RATE_LIMIT_WINDOW_MS);
    if (recent.length > 0) {
      rateLimitStore.set(key, recent);
    } else {
      rateLimitStore.delete(key);
    }
  }

  const timestamps = rateLimitStore.get(ip) || [];
  if (timestamps.length >= RATE_LIMIT_MAX_SUBMISSIONS) {
    return false;
  }

  timestamps.push(now);
  rateLimitStore.set(ip, timestamps);
  return true;
}

export default async function handler(req, res) {
  const allowedOrigin = getAllowedRequestOrigin(req);

  // CORS
  if (allowedOrigin) {
    res.setHeader('Access-Control-Allow-Origin', allowedOrigin);
    res.setHeader('Vary', 'Origin');
  }
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    if (!allowedOrigin) {
      return res.status(403).json({ error: 'Forbidden origin' });
    }
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  if (!allowedOrigin) {
    return res.status(403).json({ error: 'Forbidden origin' });
  }

  const fetchSite = req.headers['sec-fetch-site'];
  if (fetchSite && !['same-origin', 'same-site', 'none'].includes(fetchSite)) {
    return res.status(403).json({ error: 'Cross-site requests are not allowed' });
  }

  const clientIp = getClientIp(req);
  if (!consumeRateLimit(clientIp)) {
    return res.status(429).json({
      error: 'Trop de demandes envoyées. Merci de réessayer plus tard.',
    });
  }

  const { type, name, email, subject, message, website, human } = req.body || {};

  // Anti-spam : honeypot (un bot aura rempli ce champ)
  if (website) {
    return res.status(200).json({ success: true }); // faux succès pour ne pas alerter le bot
  }

  // Validation
  if (!type || !email) {
    return res.status(400).json({ error: 'Les champs type et email sont obligatoires.' });
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    return res.status(400).json({ error: 'Adresse email invalide.' });
  }
  if (human !== true) {
    return res.status(400).json({ error: 'Confirmation humaine manquante.' });
  }
  if (typeof subject === 'string' && subject.length > 200) {
    return res.status(400).json({ error: 'Objet trop long.' });
  }
  if (typeof message === 'string' && message.length > 5000) {
    return res.status(400).json({ error: 'Message trop long.' });
  }

  const typeLabels = {
    contact:     'Prise de contact',
    improvement: "Demande d'amélioration",
    correction:  'Demande de correction',
  };
  const typeLabel = typeLabels[type] || type;
  const timestamp = new Date().toISOString();

  const errors = [];

  // ─── 1. Envoi email via Resend ────────────────────────────────────────────
  const resendKey  = process.env.RESEND_API_KEY;
  const fromEmail  = process.env.CONTACT_FROM_EMAIL;
  const toEmail    = process.env.CONTACT_TO_EMAIL;

  if (!resendKey || !fromEmail || !toEmail) {
    errors.push('Email : RESEND_API_KEY, CONTACT_FROM_EMAIL ou CONTACT_TO_EMAIL non configurés.');
  } else {
    const emailSubject = subject
      ? `[FrenchNamesAustralia] ${subject}`
      : `[FrenchNamesAustralia] ${typeLabel}`;

    const htmlBody = `
      <table style="font-family:Arial,sans-serif;font-size:14px;color:#333;border-collapse:collapse;width:100%;max-width:600px">
        <tr><td colspan="2" style="background:#0056b3;color:#fff;padding:14px 18px;font-size:16px;font-weight:bold">
          Nouveau message — French Names Along the Australian Coastline
        </td></tr>
        <tr><td style="padding:10px 18px;font-weight:bold;width:160px">Date</td><td style="padding:10px 18px">${timestamp}</td></tr>
        <tr style="background:#f4f8ff"><td style="padding:10px 18px;font-weight:bold">Type</td><td style="padding:10px 18px">${typeLabel}</td></tr>
        <tr><td style="padding:10px 18px;font-weight:bold">Nom</td><td style="padding:10px 18px">${name || '—'}</td></tr>
        <tr style="background:#f4f8ff"><td style="padding:10px 18px;font-weight:bold">Email</td><td style="padding:10px 18px"><a href="mailto:${email}">${email}</a></td></tr>
        <tr><td style="padding:10px 18px;font-weight:bold">Objet</td><td style="padding:10px 18px">${subject || '—'}</td></tr>
        <tr style="background:#f4f8ff;vertical-align:top"><td style="padding:10px 18px;font-weight:bold">Message</td>
          <td style="padding:10px 18px">${message ? message.replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n+/g,' ') : '—'}</td></tr>
      </table>`;

    try {
      console.log('[contact] Tentative envoi Resend →', { from: fromEmail, to: toEmail, subject: emailSubject });
      const emailRes = await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${resendKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          from: fromEmail,
          to: [toEmail],
          reply_to: email,
          subject: emailSubject,
          html: htmlBody,
        }),
      });
      const resendBody = await emailRes.text();
      if (!emailRes.ok) {
        console.error('[contact] Resend erreur :', emailRes.status, resendBody);
        errors.push(`Email Resend : ${emailRes.status} — ${resendBody}`);
      } else {
        console.log('[contact] Resend succès :', emailRes.status, resendBody);
      }
    } catch (err) {
      console.error('[contact] Resend exception :', err.message);
      errors.push(`Email Resend (réseau) : ${err.message}`);
    }
  }

  // ─── 2. Enregistrement Google Sheet via Apps Script Web App ───────────────
  const sheetWebhook = process.env.GOOGLE_SHEET_WEBHOOK;

  if (!sheetWebhook) {
    errors.push('Google Sheet : GOOGLE_SHEET_WEBHOOK non configuré.');
  } else {
    try {
      const sheetRes = await fetch(sheetWebhook, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          timestamp,
          type: typeLabel,
          name:    name    || '',
          email,
          subject: subject || '',
          message: message || '',
        }),
      });
      if (!sheetRes.ok) {
        const detail = await sheetRes.text();
        errors.push(`Google Sheet : ${sheetRes.status} — ${detail}`);
      }
    } catch (err) {
      errors.push(`Google Sheet (réseau) : ${err.message}`);
    }
  }

  // ─── Réponse ──────────────────────────────────────────────────────────────
  if (errors.length > 0) {
    console.error('[contact] Erreurs partielles :', errors);
    // On renvoie quand même 200 si au moins l'email OU la sheet a réussi
    const totalActions = (resendKey && fromEmail ? 1 : 0) + (sheetWebhook ? 1 : 0);
    if (errors.length >= totalActions) {
      return res.status(500).json({ error: 'Échec de l\'envoi.', details: errors });
    }
  }

  return res.status(200).json({ success: true });
}
