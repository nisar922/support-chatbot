function getToken() { return localStorage.getItem("token"); }

function setToken(t) { localStorage.setItem("token", t); }

function clearToken() { localStorage.removeItem("token"); }

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function fmt(d) {
  if (!d) return "-";
  return new Date(d.endsWith("Z") ? d : d + "Z").toLocaleString();
}

async function api(path, { method = "GET", body, form, formData } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = "Bearer " + token;

  let payload;
  if (body) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  } else if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = new URLSearchParams(form);
  } else if (formData) {
    payload = formData;
  }
  const res = await fetch(path, { method, headers, body: payload });
  if (res.status === 204) return null;

  let data = null;
  try { data = await res.json(); } catch (e) {}

  if (!res.ok) {
    const msg = typeof (data && data.detail) === "string"
      ? data.detail
      : "Request failed (" + res.status + ")";
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return data;
}