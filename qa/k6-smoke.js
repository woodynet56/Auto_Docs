import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    public_health: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.REQUEST_RATE || 20),
      timeUnit: "1s",
      duration: __ENV.DURATION || "2m",
      preAllocatedVUs: 10,
      maxVUs: 50,
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500", "p(99)<1000"],
    checks: ["rate>0.99"],
  },
};

export default function () {
  const base = __ENV.BASE_URL;
  const response = http.get(`${base}/health/live`, { tags: { endpoint: "live" } });
  check(response, { "live returns 200": (result) => result.status === 200 });
  sleep(0.1);
}
