// Verifies the Phase 0 spike result: a guest socket can join a tt_session
// room and receive server-published events. Run from the app root:
//   node scripts/check_guest_socket.cjs
// then publish from the bench:
//   bench --site trivia-tap.localhost execute frappe.publish_realtime \
//     --kwargs '{"event": "tt_session_123456", "message": {"type": "check"}, "room": "tt_session_123456"}'
const path = require("path");
const { io } = require(path.join(
  __dirname,
  "../frontend/node_modules/socket.io-client"
));

const SITE = "trivia-tap.localhost";
const PIN = "123456";

const socket = io(`http://${SITE}:9000/${SITE}`, {
  extraHeaders: {
    Origin: `http://${SITE}`,
    Cookie: "sid=Guest",
  },
  reconnection: false,
});

let got_event = false;

socket.on("connect", () => {
  console.log("connected as guest:", socket.id);
  socket.emit("tt_join", PIN);
  console.log(`joined tt_session_${PIN}, waiting for a published event...`);
});

socket.on(`tt_session_${PIN}`, (data) => {
  got_event = true;
  console.log("PASS: received", JSON.stringify(data));
  process.exit(0);
});

socket.on("connect_error", (err) => {
  console.log("connect_error:", err.message);
});

setTimeout(() => {
  console.log("FAIL: no event received in 30s");
  process.exit(1);
}, 30000);
