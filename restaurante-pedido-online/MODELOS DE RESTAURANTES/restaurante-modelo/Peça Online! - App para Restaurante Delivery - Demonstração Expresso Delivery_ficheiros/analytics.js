function registerVisit(merchant, store, sessionId, year, month, day) {
  let hasCookie = Cookies.get("analytics");
  if (!hasCookie) {
    let data = getParms();
    data["url"] = window.location.host;
    data["merchant"] = merchant;
    data["store"] = store;
    data["sessionId"] = sessionId;
    data["year"] = year;
    data["month"] = month;
    data["day"] = day;

    var ajax = $.ajax({
      url: "/visit/analytics/daily",
      method: "POST",
      data: data,
    });
    ajax.done(function (msg) {
      var today = new Date();
      today.setHours(0, 0, 0, 0);

      var expires = new Date(today);
      expires.setDate(today.getDate() + 1);

      Cookies.set("analytics", true, { expires: expires });
    });
    ajax.fail(function (jqXHR, textStatus) {
      console.error("Erro ao enviar visitas");
    });
  }
}

function getParms() {
  const url = new URL(window.location.href);

  const utmParams = {};
  for (const [param, value] of url.searchParams) {
    if (param.startsWith("utm")) {
      utmParams[param] = value;
    }
  }

  return utmParams;
}
