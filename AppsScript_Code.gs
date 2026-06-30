/*  Sistem Audit Tafsir — Google Sheet backend (Apps Script Web App)
 *  ----------------------------------------------------------------
 *  CARA PASANG:
 *  1. Buat Google Sheet baru (mis. "Audit Tafsir DB").
 *  2. Extensions → Apps Script. Hapus isi default, tempel SELURUH file ini.
 *  3. Klik Deploy → New deployment → type: Web app.
 *       - Execute as: Me
 *       - Who has access: Anyone
 *     Deploy → salin "Web app URL" (diakhiri /exec).
 *  4. Tempel URL itu ke sistem audit (tombol "Atur sinkron" → Web App URL).
 *  5. Bagikan link GitHub Pages + minta tiap penilai isi nama koder.
 *
 *  Sheet otomatis dibuat: FINDINGS (temuan) & RUBRIC (skor rubrik).
 *  Tidak menyimpan apa pun yang sensitif selain hasil koding.
 */

var SHEET_F = 'FINDINGS';
var SHEET_R = 'RUBRIC';
var F_COLS = ['id','run_id','model','category','severity','status','coder','quote','source','note','updated'];
var R_COLS = ['run_id','coder','dim','value','updated'];

function _ss(){ return SpreadsheetApp.getActiveSpreadsheet(); }
function _sheet(name, cols){
  var ss=_ss(), sh=ss.getSheetByName(name);
  if(!sh){ sh=ss.insertSheet(name); sh.appendRow(cols); }
  return sh;
}
function _rows(sh, cols){
  var v=sh.getDataRange().getValues(); if(v.length<2) return [];
  var head=v[0], out=[];
  for(var i=1;i<v.length;i++){ var o={}; for(var c=0;c<head.length;c++) o[head[c]]=v[i][c]; out.push(o); }
  return out;
}
function _json(obj){
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/* GET = ambil semua data (untuk sinkron turun) */
function doGet(e){
  var f=_sheet(SHEET_F,F_COLS), r=_sheet(SHEET_R,R_COLS);
  return _json({ ok:true, findings:_rows(f,F_COLS), rubric:_rows(r,R_COLS) });
}

/* POST = simpan (untuk sinkron naik). body JSON:
   { action:'upsertFinding', finding:{...} }
   { action:'deleteFinding', id:'...' }
   { action:'setRubric', run_id, coder, dim, value }
*/
function doPost(e){
  var lock=LockService.getScriptLock();
  lock.waitLock(20000);
  try{
    var body=JSON.parse(e.postData.contents||'{}');
    var now=new Date().toISOString();
    if(body.action==='upsertFinding'){
      var sh=_sheet(SHEET_F,F_COLS), fnd=body.finding||{}, data=sh.getDataRange().getValues();
      var rowIdx=-1; for(var i=1;i<data.length;i++){ if(String(data[i][0])===String(fnd.id)){ rowIdx=i+1; break; } }
      var row=F_COLS.map(function(c){ return c==='updated'?now:(fnd[c]!=null?fnd[c]:''); });
      if(rowIdx>0) sh.getRange(rowIdx,1,1,F_COLS.length).setValues([row]);
      else sh.appendRow(row);
      return _json({ok:true});
    }
    if(body.action==='deleteFinding'){
      var sh2=_sheet(SHEET_F,F_COLS), d2=sh2.getDataRange().getValues();
      for(var j=d2.length-1;j>=1;j--){ if(String(d2[j][0])===String(body.id)) sh2.deleteRow(j+1); }
      return _json({ok:true});
    }
    if(body.action==='reset'){
      // kosongkan semua data (sisakan header). Untuk mulai bersih.
      var rf=_sheet(SHEET_F,F_COLS); if(rf.getLastRow()>1) rf.deleteRows(2, rf.getLastRow()-1);
      var rr0=_sheet(SHEET_R,R_COLS); if(rr0.getLastRow()>1) rr0.deleteRows(2, rr0.getLastRow()-1);
      return _json({ok:true});
    }
    if(body.action==='bulk'){
      // seed/replace banyak sekaligus (dipakai auto-fill). Tulis batch (cepat).
      if(body.findings && body.findings.length){
        var fs=_sheet(SHEET_F,F_COLS), fd=fs.getDataRange().getValues(), idx={};
        for(var a=1;a<fd.length;a++) idx[String(fd[a][0])]=a+1;
        var fApp=[];
        body.findings.forEach(function(fnd){
          var row=F_COLS.map(function(c){ return c==='updated'?now:(fnd[c]!=null?fnd[c]:''); });
          if(idx[String(fnd.id)]) fs.getRange(idx[String(fnd.id)],1,1,F_COLS.length).setValues([row]);
          else fApp.push(row);
        });
        if(fApp.length) fs.getRange(fs.getLastRow()+1,1,fApp.length,F_COLS.length).setValues(fApp);
      }
      if(body.rubric && body.rubric.length){
        var rs2=_sheet(SHEET_R,R_COLS), rd2=rs2.getDataRange().getValues(), ridx={};
        for(var b=1;b<rd2.length;b++) ridx[rd2[b][0]+'|'+rd2[b][1]+'|'+rd2[b][2]]=b+1;
        var rApp=[];
        body.rubric.forEach(function(rr){
          var key=rr.run_id+'|'+rr.coder+'|'+rr.dim, row=[rr.run_id,rr.coder,rr.dim,rr.value,now];
          if(ridx[key]) rs2.getRange(ridx[key],1,1,R_COLS.length).setValues([row]);
          else rApp.push(row);
        });
        if(rApp.length) rs2.getRange(rs2.getLastRow()+1,1,rApp.length,R_COLS.length).setValues(rApp);
      }
      return _json({ok:true});
    }
    if(body.action==='setRubric'){
      var sr=_sheet(SHEET_R,R_COLS), dr=sr.getDataRange().getValues(), found=-1;
      for(var k=1;k<dr.length;k++){ if(String(dr[k][0])===String(body.run_id)&&String(dr[k][1])===String(body.coder)&&String(dr[k][2])===String(body.dim)){ found=k+1; break; } }
      if(body.value===null||body.value===''){ if(found>0) sr.deleteRow(found); return _json({ok:true}); }
      var rrow=[body.run_id,body.coder,body.dim,body.value,now];
      if(found>0) sr.getRange(found,1,1,R_COLS.length).setValues([rrow]);
      else sr.appendRow(rrow);
      return _json({ok:true});
    }
    return _json({ok:false,error:'unknown action'});
  } catch(err){
    return _json({ok:false,error:String(err)});
  } finally {
    lock.releaseLock();
  }
}
