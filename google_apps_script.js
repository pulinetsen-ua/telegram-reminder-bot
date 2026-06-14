// ─── Google Apps Script ────────────────────────────────────────────────────
// При обновлении: Развернуть → Управление развёртываниями → карандаш →
// Новая версия → Развернуть. URL не изменится.
// ──────────────────────────────────────────────────────────────────────────

function parseDate(str) {
  // Парсит дату формата ДД.ММ.ГГ
  var parts = str.trim().split(".");
  if (parts.length !== 3) return null;
  return new Date(2000 + parseInt(parts[2]), parseInt(parts[1]) - 1, parseInt(parts[0]));
}

// Запись новой задачи (POST)
function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = JSON.parse(e.postData.contents);
    sheet.appendRow([data.id, data.date, data.description]);
    return ContentService
      .createTextOutput(JSON.stringify({ status: "ok" }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// GET: чтение задач на дату или удаление устаревших
function doGet(e) {
  try {
    var action = e.parameter.action;

    // Возвращает задачи на указанную дату
    if (action === "get_today") {
      var date = e.parameter.date;
      var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
      var rows = sheet.getDataRange().getValues();
      var tasks = [];
      for (var i = 1; i < rows.length; i++) {
        var rowDate = String(rows[i][1]).trim();
        if (rowDate === date) {
          tasks.push({
            id:          String(rows[i][0]).trim(),
            date:        rowDate,
            description: String(rows[i][2]).trim()
          });
        }
      }
      return ContentService
        .createTextOutput(JSON.stringify({ status: "ok", tasks: tasks }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // Удаляет строки с датой раньше сегодняшней
    if (action === "cleanup") {
      var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
      var today = new Date();
      today.setHours(0, 0, 0, 0);
      var rows = sheet.getDataRange().getValues();
      var toDelete = [];

      for (var i = rows.length - 1; i >= 1; i--) { // снизу вверх чтобы индексы не съезжали
        var d = parseDate(String(rows[i][1]));
        if (d && d < today) {
          toDelete.push(i + 1); // +1 потому что getValues() начинает с 0, а строки с 1
        }
      }

      for (var j = 0; j < toDelete.length; j++) {
        sheet.deleteRow(toDelete[j]);
      }

      return ContentService
        .createTextOutput(JSON.stringify({ status: "ok", deleted: toDelete.length }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: "unknown action" }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
