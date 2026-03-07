// api/contact.js - Vercel Serverless Function
// Reçoit les données du formulaire de contact, envoie un email via Resend
// et enregistre la soumission dans la Google Sheet via Apps Script Web App.
//
// Variables d'environnement requises (Vercel Dashboard > Settings > Environment Variables) :
//   RESEND_API_KEY         — clé API Resend (https://resend.com)
//   CONTACT_FROM_EMAIL     — adresse expéditrice vérifiée sur Resend (ex: contact@frenchnamesaustralia.com)
//   CONTACT_TO_EMAIL       — destinataire (dmbreelle@gmail.com)
//   GOOGLE_SHEET_WEBHOOK   — URL du Google Apps Script Web App déployé sur la feuille

export default async function handler(req, res) {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { type, name, email, subject, message } = req.body || {};

  // Validation
  if (!type || !email) {
    return res.status(400).json({ error: 'Les champs type et email sont obligatoires.' });
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    return res.status(400).json({ error: 'Adresse email invalide.' });
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
  const toEmail    = process.env.CONTACT_TO_EMAIL || 'dmbreelle@gmail.com';

  if (!resendKey || !fromEmail) {
    errors.push('Email : RESEND_API_KEY ou CONTACT_FROM_EMAIL non configurés.');
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
          <td style="padding:10px 18px;white-space:pre-wrap">${message ? message.replace(/</g,'&lt;').replace(/>/g,'&gt;') : '—'}</td></tr>
        <tr><td colspan="2" style="padding:14px 18px;font-size:12px;color:#888;border-top:1px solid #e0e0e0">
          Soumis via le formulaire de contact du site frenchnamesaustralia.com
        </td></tr>
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
