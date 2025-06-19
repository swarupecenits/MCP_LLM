import { execSync } from "child_process";
import http from "http";
/* eslint-disable no-console */

function execAz(cmd: string): string | undefined {
  try {
    const response = execSync(`az ${cmd}`, {
      encoding: "utf-8",
    });
    return response;
  } catch (err) {
    if (err.status !== 1) {
      throw err;
    }
    return undefined;
  }
}

function getCacheHeaders(tokenJson?: string): { [name: string]: string } {
  // for long running operations, let token refresh if close to expiry
  // this value should be <= 5min because the `az` cli command also caches the last token fetched until 5 min before expiry
  const validUntilBeforeExpirySec = 5 * 60;
  try {
    const auth: { expiresOn: string } | undefined = tokenJson ? JSON.parse(tokenJson) : undefined;
    if (auth && auth.expiresOn) {
      const expiresOn = new Date(auth.expiresOn);
      const cacheExpires = new Date(expiresOn.getTime() - validUntilBeforeExpirySec * 1000);
      return {
        "Cache-Control": "private",
        Expires: cacheExpires.toUTCString(),
      };
    }
  } catch (e) {
    console.error("parsing token failed", e, tokenJson);
  }
  return {};
}

http
  .createServer(async (request, response) => {
    function setResponse(code: number, content?: string, headers: { [name: string]: string } = {}): void {
      response.writeHead(code, {
        "Content-Type": "text/plain",
        "Access-Control-Allow-Origin": (request.headers && request.headers.origin) || "self",
        // wildcard not supported by Safari, so try to OK whatever headers requested first
        "Access-Control-Allow-Headers": (request.headers && request.headers["access-control-request-headers"]) || "*",
        ...headers,
      });
      response.end(content);
    }
    try {
      if (request.method === "OPTIONS") {
        setResponse(200);
      } else if (!request.url) {
        setResponse(404, `Empty url`);
      } else {
        const urlArr = request.url.split("/");
        switch (urlArr[1]) {
          case "token":
            const tokenJson = execAz("account get-access-token -o json");
            const headers = getCacheHeaders(tokenJson);
            setResponse(200, tokenJson, headers);
            break;
          case "logout":
            setResponse(200, execAz("logout"));
            break;
          case "login":
            setResponse(200, execAz("login"));
            break;
          case "user":
            setResponse(200, execAz("account show -o json"));
            break;
          case "httpcode":
            setResponse(parseInt(urlArr[2], 10) || 404, urlArr[2]);
            break;
          default:
            setResponse(404, `Unsupported url ${request.url}`);
        }
      }
    } catch (err) {
      response.writeHead(500);
      // CodeQL [SM01524] logging stack traces on the server prevents remote users from directly accessing the information.
      response.write(JSON.stringify(err));
      response.end();
    }
  })
  .listen(3001);

console.log("Token Server running at http://127.0.0.1:3001/");
