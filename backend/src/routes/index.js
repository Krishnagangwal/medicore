const express = require('express');

const authRoutes = require('./auth.routes');
const patientsRoutes = require('./patients.routes');
const encountersRoutes = require('./encounters.routes');
const vitalsRoutes = require('./vitals.routes');
const medicationsRoutes = require('./medications.routes');
const predictionsRoutes = require('./predictions.routes');
const notificationsRoutes = require('./notifications.routes');
const gatewayRoutes = require('./gateway.routes');

const router = express.Router();

router.use('/auth', authRoutes);
router.use('/patients', patientsRoutes);
router.use('/encounters', encountersRoutes);
router.use('/vitals', vitalsRoutes);
router.use('/medications', medicationsRoutes);
router.use('/predictions', predictionsRoutes);
router.use('/notifications', notificationsRoutes);
router.use('/gateway', gatewayRoutes);

module.exports = router;
