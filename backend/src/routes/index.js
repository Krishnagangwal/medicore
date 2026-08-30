const express = require('express');

const authRoutes = require('./auth.routes');
const patientsRoutes = require('./patients.routes');
const encountersRoutes = require('./encounters.routes');
const vitalsRoutes = require('./vitals.routes');
const medicationsRoutes = require('./medications.routes');
const predictionsRoutes = require('./predictions.routes');
const notificationsRoutes = require('./notifications.routes');
const gatewayRoutes = require('./gateway.routes');
const hospitalsRoutes = require('./hospitals.routes');
const hospitalAdminRoutes = require('./hospitalAdmin.routes');

const router = express.Router();

router.use('/auth', authRoutes);
router.use('/patients', patientsRoutes);
router.use('/hospitals', hospitalsRoutes);
router.use('/hospital', hospitalAdminRoutes);

// Nested reads (mergeParams routers) — must come before the flat
// '/encounters' mount so :encounterId sub-resources resolve first.
router.use('/encounters/:encounterId/vitals', vitalsRoutes);
router.use('/encounters/:encounterId/medications', medicationsRoutes);
router.use('/encounters/:encounterId/predictions', predictionsRoutes);
router.use('/encounters', encountersRoutes);

router.use('/vitals', vitalsRoutes);
router.use('/medications', medicationsRoutes);
router.use('/notifications', notificationsRoutes);
router.use('/gateway', gatewayRoutes);

module.exports = router;
