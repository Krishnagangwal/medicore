require('dotenv').config();
const http = require('http');
const app = require('./app');
const { initSockets } = require('./sockets/index');
const { startScoringJob } = require('./jobs/scoringJob');

const PORT = process.env.PORT || 5000;

const httpServer = http.createServer(app);
initSockets(httpServer);
startScoringJob();

httpServer.listen(PORT, () => {
  console.log(`MediCore backend listening on port ${PORT}`);
});
