const nodemailer = require('nodemailer')

const SMTP_CONFIGURED = !!(process.env.SMTP_USER && process.env.SMTP_PASS)

const transporter = SMTP_CONFIGURED
  ? nodemailer.createTransport({
      host: process.env.SMTP_HOST || 'smtp.gmail.com',
      port: parseInt(process.env.SMTP_PORT || '587'),
      secure: false,
      auth: {
        user: process.env.SMTP_USER,
        pass: process.env.SMTP_PASS
      },
      // Some networks advertise IPv6 but can't actually route it, which
      // makes Node's "happy eyeballs" DNS resolution pick an unreachable
      // IPv6 address for smtp.gmail.com and fail with ENETUNREACH. Forcing
      // IPv4 sidesteps that instead of depending on the network being fixed.
      family: 4
    })
  : null

async function sendMail(options) {
  if (!SMTP_CONFIGURED) {
    console.log('[Email] SMTP not configured — would have sent:')
    console.log(`  To: ${options.to}`)
    console.log(`  Subject: ${options.subject}`)
    console.log(`  Body preview: ${options.text || '(HTML email)'}`)
    return
  }
  try {
    await transporter.sendMail({
      from: `"MediCore Platform" <${process.env.SMTP_USER}>`,
      ...options
    })
    console.log(`[Email] Sent to ${options.to}: ${options.subject}`)
  } catch (err) {
    console.error('[Email] Failed to send:', err.message)
    // Never crash the server on email failure
  }
}

async function sendHospitalApprovalEmail({ to, hospitalName, adminName, tempPassword, resetToken }) {
  const loginUrl = process.env.FRONTEND_URL || 'http://localhost:3001'
  const resetUrl = `${loginUrl}/reset-password?token=${resetToken}`
  await sendMail({
    to,
    subject: `MediCore — ${hospitalName} has been approved`,
    text: `
Welcome to MediCore, ${adminName}.

Your hospital "${hospitalName}" has been approved.

Login at: ${loginUrl}
Email: ${to}
Temporary Password: ${tempPassword}

Prefer to set your own password instead? Use this link (valid 1 hour):
${resetUrl}

As hospital admin you can now invite nurses and doctors.
Change your password after first login.

— MediCore Team
    `.trim()
  })
}

async function sendStaffInviteEmail({ to, staffName, hospitalName, tempPassword, role, resetToken }) {
  const loginUrl = process.env.FRONTEND_URL || 'http://localhost:3001'
  const resetUrl = `${loginUrl}/reset-password?token=${resetToken}`
  await sendMail({
    to,
    subject: `MediCore — You have been invited to ${hospitalName}`,
    text: `
Hello ${staffName},

You have been added as ${role} at ${hospitalName} on MediCore.

Login at: ${loginUrl}
Email: ${to}
Temporary Password: ${tempPassword}

Prefer to set your own password instead? Use this link (valid 1 hour):
${resetUrl}

— MediCore Team
    `.trim()
  })
}

module.exports = { sendHospitalApprovalEmail, sendStaffInviteEmail }
