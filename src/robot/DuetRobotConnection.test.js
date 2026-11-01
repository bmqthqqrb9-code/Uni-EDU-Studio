import assert from 'node:assert/strict';
import test from 'node:test';
import { DuetRobotConnection } from './DuetRobotConnection.js';

test('DUET connection uses isolated connect, status, run, stop and disconnect endpoints', async () => {
  const requests = [];
  const connection = new DuetRobotConnection(async (...args) => {
    requests.push(args);
    return { status: 'connected' };
  });

  await connection.connect();
  await connection.status();
  await connection.run('duet.move(0.2, 0, 0, 1)');
  await connection.stop();
  await connection.disconnect();

  assert.deepEqual(requests.map(([url]) => url), [
    '/api/duet/connect',
    '/api/duet/status',
    '/api/duet/run',
    '/api/duet/stop',
    '/api/duet/disconnect',
  ]);
  assert.deepEqual(requests[1][1], { cache: 'no-store' });
  assert.deepEqual(JSON.parse(requests[2][1].body), { code: 'duet.move(0.2, 0, 0, 1)' });
});

test('DUET connection rejects legacy commands before sending a request', async () => {
  const requests = [];
  const connection = new DuetRobotConnection(async (...args) => {
    requests.push(args);
  });
  await assert.rejects(connection.run('robot.walk(1)'), /Unsupported statement/);
  assert.deepEqual(requests, []);
});

test('DUET commissioning exposes isolated evidence and review endpoints', async () => {
  const requests = [];
  const connection = new DuetRobotConnection(async (...args) => {
    requests.push(args);
    return { status: 'passed' };
  });

  await connection.commissioningStatus();
  await connection.commissioningEvidence();
  await connection.startCommissioning();
  await connection.runCommissioningStep(2);
  await connection.reviewCommissioningStep(2, {
    passed: true,
    observed: true,
    observedResult: 'Observed the expected response.',
    notes: 'Clear area.',
  });

  assert.deepEqual(requests.map(([url]) => url), [
    '/api/duet/commissioning',
    '/api/duet/commissioning/evidence',
    '/api/duet/commissioning/start',
    '/api/duet/commissioning/step',
    '/api/duet/commissioning/review',
  ]);
  assert.deepEqual(requests[1][1], { cache: 'no-store' });
  assert.deepEqual(JSON.parse(requests[4][1].body), {
    step_index: 2,
    passed: true,
    observed: true,
    observed_result: 'Observed the expected response.',
    notes: 'Clear area.',
  });
});

test('DUET connection rejects empty programs before sending a request', async () => {
  const requests = [];
  const connection = new DuetRobotConnection(async (...args) => {
    requests.push(args);
  });
  await assert.rejects(connection.run('# no commands'), /contains no commands/);
  assert.deepEqual(requests, []);
});

test('DUET connection requires authenticated request transport', () => {
  assert.throws(() => new DuetRobotConnection(), /authenticated request function/);
});
