const { Resend } = require('resend')

const RESEND_CONFIGURED = !!process.env.RESEND_API_KEY

const resend = RESEND_CONFIGURED ? new Resend(process.env.RESEND_API_KEY) : null

// Resend's shared sandbox sender — works with no setup, but Resend only
// lets a sandbox sender deliver to the email address your Resend account
// itself was signed up with. To actually email real hospital admins/staff,
// verify a domain at resend.com/domains and set RESEND_FROM_EMAIL to an
// address on it (e.g. noreply@yourdomain.com).
const FROM_EMAIL = process.env.RESEND_FROM_EMAIL || 'MediCore <onboarding@resend.dev>'

async function sendMail(options) {
  console.log('🔥 SENDMAIL FUNCTION CALLED 🔥')
  console.log('[Email] RESEND configured:', RESEND_CONFIGURED)
  console.log('[Email] From:', FROM_EMAIL)
  console.log('[Email] To:', options.to)
  console.log('[Email] Subject:', options.subject)

  if (!RESEND_CONFIGURED) {
    console.log('[Email] RESEND_API_KEY not configured')
    return
  }
  try {
    const { data, error } = await resend.emails.send({
      from: FROM_EMAIL,
      to: options.to,
      subject: options.subject,
      text: options.text
    })
    if (error) {
      console.error('[Email] Failed to send:', error.message || error)
      return
    }
    console.log(`[Email] Sent to ${options.to}: ${options.subject} (id ${data?.id})`)
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
    subject: `MediCore - You have been invited to ${hospitalName}`,
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
