/**
 * Google Sheets CMS API - Evolution Stables
 * 
 * Exposes Google Sheet rows as a clean JSON API endpoint.
 * Paste this into Extensions -> Apps Script on your Google Sheet.
 * Deploy as Web App -> Execute as "Me" -> Who has access: "Anyone".
 */

function doGet(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
    var data = sheet.getDataRange().getValues();
    
    if (data.length <= 1) {
      return ContentService.createTextOutput(JSON.stringify([]))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    var headers = data[0];
    var result = [];
    
    for (var i = 1; i < data.length; i++) {
      var row = data[i];
      var obj = {};
      var hasValue = false;
      
      for (var j = 0; j < headers.length; j++) {
        var header = headers[j].toString().trim();
        if (!header) continue;
        
        // Convert header to lowercase snake_case key
        var key = header.toLowerCase()
                        .replace(/[^a-z0-9_]+/g, '_')
                        .replace(/^_+|_+$/g, '');
        
        var val = row[j];
        
        // Format dates to ISO strings for JSON safety
        if (val instanceof Date) {
          val = val.toISOString();
        }
        
        obj[key] = val;
        if (val !== "" && val !== null && val !== undefined) {
          hasValue = true;
        }
      }
      
      // Only append row if it has at least one value (skips blank rows)
      if (hasValue) {
        result.push(obj);
      }
    }
    
    return ContentService.createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON)
      .setHeaders({
        "Access-Control-Allow-Origin": "*"
      });
      
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      "error": error.toString()
    }))
    .setMimeType(ContentService.MimeType.JSON)
    .setHeaders({
      "Access-Control-Allow-Origin": "*"
    });
  }
}
