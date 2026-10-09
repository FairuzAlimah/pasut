const DATA = {
  tide: "data/tide_all.csv",
  validation: "data/validation_eot20_all.csv",
  metrics: "data/metrics_eot20_all.csv",
  stations: "data/stations.csv",
  bigMetrics: "data/metrics_validasi_big_2025.csv",
  bigIndex: "data/validasi_big_index.csv"
};
const MONTHS=["January","February","March","April","May","June","July","August","September","October","November","December"];
const MONTH_ID={"January":"Januari","February":"Februari","March":"Maret","April":"April","May":"Mei","June":"Juni","July":"Juli","August":"Agustus","September":"September","October":"Oktober","November":"November","December":"Desember"};
let tide=[], validation=[], metrics=[], stations=[], bigMetrics=[], bigIndex=[];
let map, markers=[], mapHome=[-7.94,110.22], mapZoom=9;

const PRINT_W = 700;          // lebar gambar (px), setara area cetak A4 portrait
const PRINT_SCALE = 2;        // resolusi gambar (2x agar tajam)
const PRINT_H_FACTOR = 0.9;   // tinggi grafik cetak = 90% tinggi layar
let rawNewPlot = null;

function plotEl(gd){ return typeof gd === "string" ? document.getElementById(gd) : gd; }
function cloneDeep(o){ try{ return structuredClone(o); }catch(_){ return JSON.parse(JSON.stringify(o)); } }

function markStale(el){
  if(!el || !el.classList) return;
  el._ptok = (el._ptok || 0) + 1;            // batalkan pembuatan gambar yang sedang berjalan
  clearTimeout(el._pt);
  el.classList.remove("pimg-ready");
  const img = el.nextElementSibling;
  if(img && img.classList.contains("print-img")) img.removeAttribute("src");
}
function scheduleImage(el){
  if(!el || !el.closest("#tab-dashboard")) return;   // tab lain dibuat saat tombol cetak ditekan
  clearTimeout(el._pt);
  el._pt = setTimeout(()=>buildImage(el), 500);
}
async function renderPrintImage(el){
  if(!el || !Array.isArray(el.data) || !el.layout || !rawNewPlot) return null;
  const lay = cloneDeep(el.layout), data = cloneDeep(el.data);
  const H = Math.round((Number(lay.height) || 450) * PRINT_H_FACTOR);
  lay.autosize = false; lay.width = PRINT_W; lay.height = H;
  lay.margin = Object.assign({l:70,r:30,t:90,b:65}, lay.margin || {});

  if(lay.title){
    const t = typeof lay.title === "string" ? {text:lay.title} : lay.title;
    t.font = Object.assign({}, t.font, {size:15});
    // judul panjang dipecah dua baris sebelum tanda kurung agar muat di lebar kertas
    if(t.text && t.text.length > 52 && t.text.indexOf("<br>") < 0){
      const i = t.text.indexOf(" (");
      if(i > 0){ t.text = t.text.slice(0,i) + "<br>" + t.text.slice(i+1); lay.margin.t = Math.max(lay.margin.t, 95); }
    }
    lay.title = t;
  }
  if(lay.legend) lay.legend.font = Object.assign({}, lay.legend.font, {size:10});

  const tmp = document.createElement("div");
  tmp.style.cssText = `position:fixed;left:-99999px;top:0;width:${PRINT_W}px;height:${H}px;pointer-events:none`;
  document.body.appendChild(tmp);
  try{
    await rawNewPlot(tmp, data, lay, {staticPlot:true, displayModeBar:false, responsive:false});
    return await Plotly.toImage(tmp, {format:"png", width:PRINT_W, height:H, scale:PRINT_SCALE});
  } finally {
    try{ Plotly.purge(tmp); }catch(_){}
    tmp.remove();
  }
}
async function buildImage(el){
  const token = el._ptok || 0;
  let url = null;
  try{ url = await renderPrintImage(el); }catch(e){ console.warn("Gagal membuat gambar cetak:", e); }
  if(!url || token !== (el._ptok || 0)) return;      // grafik sudah berubah lagi
  let img = el.nextElementSibling;
  if(!img || !img.classList.contains("print-img")){
    img = document.createElement("img");
    img.className = "print-img";
    img.alt = "Grafik";
    el.after(img);
  }
  img.src = url;
  el.classList.add("pimg-ready");
}
function printableCharts(){
  const all = document.body.classList.contains("print-all");
  return [...document.querySelectorAll(".chart")].filter(el =>
    Array.isArray(el.data) && (all || el.closest("#tab-dashboard"))
  );
}
async function ensurePrintImages(){
  await Promise.all(printableCharts().map(async el=>{
    if(!el.classList.contains("pimg-ready")){ clearTimeout(el._pt); await buildImage(el); }
  }));
}
(function patchPlotly(){
  if(!window.Plotly) return;
  rawNewPlot = Plotly.newPlot.bind(Plotly);
  const rawPurge = Plotly.purge.bind(Plotly);
  Plotly.newPlot = function(gd, ...rest){
    const el = plotEl(gd);
    markStale(el);
    const p = rawNewPlot(gd, ...rest);
    p.then(()=>scheduleImage(el));
    return p;
  };
  Plotly.purge = function(gd){
    markStale(plotEl(gd));
    return rawPurge(gd);
  };
})();


function parseCSV(text){
  const rows = [];
  let row = [], cell = "", quoted = false;

  for(let i = 0; i < text.length; i++){
    const ch = text[i];

    if(ch === '"'){
      if(quoted && text[i + 1] === '"'){
        cell += '"';
        i++;
      } else {
        quoted = !quoted;
      }
    } else if(ch === "," && !quoted){
      row.push(cell);
      cell = "";
    } else if((ch === "\n" || ch === "\r") && !quoted){
      if(ch === "\r" && text[i + 1] === "\n") i++;
      row.push(cell);
      cell = "";
      if(row.some(v => String(v).trim() !== "")){
        rows.push(row);
      }
      row = [];
    } else {
      cell += ch;
    }
  }

  if(cell !== "" || row.length){
    row.push(cell);
    if(row.some(v => String(v).trim() !== "")) rows.push(row);
  }

  if(!rows.length) return [];

  const headers = rows[0].map(h => String(h).replace(/^\uFEFF/, "").trim());

  return rows.slice(1).map(values => {
    const obj = {};
    headers.forEach((h, i) => {
      obj[h] = (values[i] ?? "").trim();
    });
    return obj;
  });
}

function csv(url){
  return fetch(url)
    .then(r => {
      if(!r.ok) throw new Error(`Tidak dapat membaca ${url} (HTTP ${r.status})`);
      return r.text();
    })
    .then(parseCSV);
}
function num(v){const x=Number(v);return Number.isFinite(x)?x:null}
function fmt(v,d=3){const x=num(v);return x===null?"-":x.toFixed(d)}
function monthName(date){return new Date(date).toLocaleString("en-US",{month:"long",timeZone:"UTC"})}
function esc(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}

/* Gaya kartu kini ada di style.css (.stat-card .label/.value/.unit) agar bisa diatur untuk cetak */
function card(title,value,unit="",accent="#0d1c42"){
  return `<div class="stat-card" style="--accent:${accent}">
    <div class="label">${esc(title)}</div>
    <div class="value">${esc(value)}</div>
    <div class="unit">${esc(unit)}</div>
  </div>`;
}

function setupSelectors(){
  const stationsNames=[...new Set(stations.map(x=>x.station).filter(Boolean))].sort();
  const years=[...new Set(tide.map(x=>num(x.year)).filter(Boolean))].sort((a,b)=>a-b);
  stationFill("station",stationsNames); stationFill("daily-station",stationsNames);
  yearFill("year",years);
  document.getElementById("month").innerHTML=MONTHS.map(m=>`<option value="${m}">${MONTH_ID[m]}</option>`).join("");
  if(years.length) document.getElementById("year").value=years[0];
  if(stationsNames.length) {document.getElementById("station").value=stationsNames[0];document.getElementById("daily-station").value=stationsNames[0]}
  const dates=tide.map(x=>new Date(x.datetime_wib)).filter(d=>!isNaN(d)).sort((a,b)=>a-b);
  if(dates.length){const d=dates[0];document.getElementById("daily-date").value=d.toISOString().slice(0,10);document.getElementById("daily-date").min=dates[0].toISOString().slice(0,10);document.getElementById("daily-date").max=dates.at(-1).toISOString().slice(0,10)}
  const bigStations=[...new Set(bigIndex.map(x=>x.station_code).filter(Boolean))].sort();
  document.getElementById("big-station").innerHTML=bigStations.map(s=>`<option value="${s}">${s==="GLGH"?"GLGH - Glagah":s==="SADG"?"SADG - Sadeng":s}</option>`).join("");
  updateBigMonths();
}
function stationFill(id,arr){document.getElementById(id).innerHTML=arr.map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join("")}
function yearFill(id,arr){document.getElementById(id).innerHTML=arr.map(y=>`<option value="${y}">${y}</option>`).join("")}

function createWeeks(year,month){
  const start=new Date(Date.UTC(year,month-1,1)), end=new Date(Date.UTC(month===12?year+1:year,month===12?0:month,1));
  const first=new Date(start); first.setUTCDate(start.getUTCDate()-start.getUTCDay()+1-(start.getUTCDay()===0?7:0));
  const weeks=[]; let cur=first, n=1;
  while(cur<end){
    const next=new Date(cur);next.setUTCDate(next.getUTCDate()+7);
    const ws=new Date(Math.max(cur.getTime(),start.getTime())), we=new Date(Math.min(next.getTime(),end.getTime()));
    if(ws<we){const display=new Date(we);display.setUTCHours(display.getUTCHours()-1);weeks.push({week_in_month:n,week_start:ws,week_end:we,display_end:display});n++}
    cur=next;
  } return weeks;
}
function weeklyStats(rows,year,month){
  const weeks=createWeeks(year,month), out=[];
  for(const w of weeks){
    const r=rows.filter(x=>{const d=new Date(x.datetime_wib);return d>=w.week_start&&d<w.week_end});
    if(!r.length)continue;
    const vals=r.map(x=>num(x.tide_m)).filter(v=>v!==null);
    if(!vals.length)continue;
    const min=Math.min(...vals),max=Math.max(...vals),mean=vals.reduce((a,b)=>a+b,0)/vals.length;
    out.push({week_in_month:w.week_in_month,week_of_year:0,start_date:w.week_start.toISOString().slice(0,10),end_date:w.display_end.toISOString().slice(0,10),jumlah_data_valid:vals.length,minimum_m:min,maximum_m:max,mean_m:mean,range_m:max-min});
  } return out;
}

function filteredTide(){
  const st=document.getElementById("station").value, year=Number(document.getElementById("year").value), month=document.getElementById("month").value;
  return tide.filter(r=>r.station===st&&Number(r.year)===year&&monthName(r.datetime_wib)===month).sort((a,b)=>new Date(a.datetime_wib)-new Date(b.datetime_wib));
}
function updateDashboard(){
  const st=document.getElementById("station").value,year=Number(document.getElementById("year").value),month=document.getElementById("month").value;
  const rows=filteredTide(), vals=rows.map(r=>num(r.tide_m)).filter(v=>v!==null);
  const status=document.getElementById("status");
  if(!rows.length){status.textContent="Data tidak tersedia untuk kombinasi stasiun, tahun, dan bulan ini.";status.className="status error";document.getElementById("summary-cards").innerHTML="";Plotly.purge("tide-chart");Plotly.purge("weekly-chart");return}
  status.textContent=`${st} · ${MONTH_ID[month]} ${year} · ${rows.length.toLocaleString("id-ID")} data valid`;
  status.className="status";
  const min=Math.min(...vals),max=Math.max(...vals),mean=vals.reduce((a,b)=>a+b,0)/vals.length;
  document.getElementById("summary-cards").innerHTML=card("Elevasi Minimum",fmt(min),"m","#5dade2")+card("Elevasi Maksimum",fmt(max),"m","#f5b041")+card("MSL / Rata-rata",fmt(mean),"m","#34495e")+card("Jumlah Data",rows.length.toLocaleString("id-ID"),"data","#0d1c42");
  const hi=rows.reduce((a,b)=>num(a.tide_m)>num(b.tide_m)?a:b),lo=rows.reduce((a,b)=>num(a.tide_m)<num(b.tide_m)?a:b);
  Plotly.newPlot("tide-chart",[
    {x:rows.map(r=>r.datetime_wib),y:rows.map(r=>num(r.tide_m)),type:"scatter",mode:"lines",name:"Prediksi Pasut",line:{width:2,color:"#1f6f8b"},hovertemplate:"<b>Waktu:</b> %{x}<br><b>Elevasi:</b> %{y:.3f} m<extra></extra>"},
    {x:[rows[0].datetime_wib,rows.at(-1).datetime_wib],y:[mean,mean],type:"scatter",mode:"lines",name:`MSL (Mean Sea Level) = ${fmt(mean)} m`,line:{color:"#34495e",dash:"dash",width:1.6},visible:"legendonly"},
    {x:[hi.datetime_wib],y:[num(hi.tide_m)],type:"scatter",mode:"markers+text",name:"Pasang tertinggi",text:[`Pasang tertinggi: ${fmt(hi.tide_m)} m`],textposition:"top center",textfont:{size:10,color:"#1e8449"},marker:{symbol:"triangle-up",size:12,color:"#1e8449"}},
    {x:[lo.datetime_wib],y:[num(lo.tide_m)],type:"scatter",mode:"markers+text",name:"Surut terendah",text:[`Surut terendah: ${fmt(lo.tide_m)} m`],textposition:"bottom center",textfont:{size:10,color:"#c0392b"},marker:{symbol:"triangle-down",size:12,color:"#c0392b"}}
  ],{
    title:{text:`Prediksi Pasang Surut GOT4.10 - ${st} ${MONTH_ID[month]} ${year} (elevasi terhadap MSL, satuan meter)`,x:0.02,xanchor:"left",font:{size:17,color:"#0D1C42"}},
    xaxis:{title:"Tanggal dan Waktu (WIB)",showgrid:true,gridcolor:"#edf1f3"},
    yaxis:{title:"Elevasi Pasang Surut terhadap MSL (m)",showgrid:true,gridcolor:"#edf1f3",zeroline:true,zerolinecolor:"#b7c4cc"},
    hovermode:"x unified",template:"plotly_white",height:550,
    margin:{l:70,r:30,t:105,b:70},paper_bgcolor:"white",plot_bgcolor:"white",
    font:{family:"Poppins, Arial, sans-serif",color:"#33415c"},
    legend:{orientation:"h",yanchor:"bottom",y:1.03,xanchor:"right",x:1,bgcolor:"rgba(255,255,255,.96)",bordercolor:"#d8e0e5",borderwidth:1,font:{size:11}}
  },{responsive:true,displaylogo:false});
  const ws=weeklyStats(rows,year,MONTHS.indexOf(month)+1);
  Plotly.newPlot("weekly-chart",[
    {x:ws.map(x=>x.week_in_month),y:ws.map(x=>x.minimum_m),type:"bar",name:"Minimum (m)",marker:{color:"#5dade2"}},
    {x:ws.map(x=>x.week_in_month),y:ws.map(x=>x.maximum_m),type:"bar",name:"Maksimum (m)",marker:{color:"#f5b041"}},
    {x:ws.map(x=>x.week_in_month),y:ws.map(x=>x.mean_m),type:"scatter",mode:"lines+markers",name:"Rata-rata mingguan (m)",line:{color:"#117864",width:2}},
    {x:[ws[0]?.week_in_month,ws.at(-1)?.week_in_month],y:[mean,mean],type:"scatter",mode:"lines",name:`MSL bulanan = ${fmt(mean)} m`,line:{color:"#34495e",dash:"dot",width:1.6},visible:"legendonly"}
  ],{
    title:{text:`Statistik Mingguan - ${st} - ${MONTH_ID[month]} ${year} (satuan: meter terhadap MSL)`,x:0.02,xanchor:"left",y:0.97,yanchor:"top",font:{size:17,color:"#0D1C42"}},
    xaxis:{title:"Minggu",showgrid:false},yaxis:{title:"Elevasi terhadap MSL (m)",showgrid:true,gridcolor:"#edf1f3",zeroline:true,zerolinecolor:"#b7c4cc"},
    barmode:"group",template:"plotly_white",height:500,margin:{l:65,r:25,t:95,b:65},
    paper_bgcolor:"white",plot_bgcolor:"white",font:{family:"Poppins, Arial, sans-serif",color:"#33415c"},
    legend:{orientation:"h",yanchor:"bottom",y:1.05,xanchor:"right",x:1,bgcolor:"rgba(255,255,255,.96)",bordercolor:"#d8e0e5",borderwidth:1,font:{size:11}}
  },{responsive:true,displaylogo:false});
  renderWeeklyTable(ws); updateValidation(st,year,month); updateMap(st,false);
}
function renderWeeklyTable(ws){
  const cols=["week_in_month","start_date","end_date","jumlah_data_valid","minimum_m","maximum_m","mean_m","range_m"];
  const heads=["Minggu ke-","Tanggal Mulai","Tanggal Akhir","Jumlah Data","Minimum (m)","Maksimum (m)","MSL / Rata-rata (m)","Range (m)"];
  document.getElementById("weekly-table").innerHTML=`<thead><tr>${heads.map(h=>`<th>${h}</th>`).join("")}</tr></thead><tbody>${ws.map(r=>`<tr>${cols.map((c,i)=>`<td>${i>=4?fmt(r[c]):(r[c]??"-")}</td>`).join("")}</tr>`).join("")}</tbody>`;
}
function updateValidation(st,year,month){
  const rows=validation.filter(r=>r.station===st&&Number(r.year)===year&&r.month===month).sort((a,b)=>new Date(a.datetime_utc)-new Date(b.datetime_utc));
  const met=metrics.find(r=>r.station===st&&Number(r.year)===year&&r.month===month);
  if(!rows.length){
    document.getElementById("validation-cards").innerHTML=card("Status","-","Data validasi tidak tersedia","#a8453a");
    Plotly.purge("validation-chart");
    return;
  }

  let rmse=met?num(met.rmse_m):null,
      mae=met?num(met.mae_m):null,
      r=met?num(met.korelasi_r):null,
      d=met?num(met.willmott_d):null;

  if(!met){
    const dif=rows.map(x=>num(x.tide_m_got410)-num(x.tide_m_eot20)).filter(Number.isFinite);
    rmse=Math.sqrt(dif.reduce((s,x)=>s+x*x,0)/dif.length);
    mae=dif.reduce((s,x)=>s+Math.abs(x),0)/dif.length;
    const a=rows.map(x=>num(x.tide_m_got410)), b=rows.map(x=>num(x.tide_m_eot20));
    const av=a.reduce((s,x)=>s+x,0)/a.length, bv=b.reduce((s,x)=>s+x,0)/b.length;
    const numr=a.reduce((s,x,i)=>s+(x-av)*(b[i]-bv),0);
    const denr=Math.sqrt(a.reduce((s,x)=>s+(x-av)**2,0)*b.reduce((s,x)=>s+(x-bv)**2,0));
    r=denr?numr/denr:null;
  }

  document.getElementById("validation-cards").innerHTML=
    card("RMSE",fmt(rmse,4),"m","#1f6f8b")+
    card("MAE",fmt(mae,4),"m","#e08e2b")+
    card("Korelasi (r)",fmt(r,4),"","#8e44ad")+
    card("Willmott's d",fmt(d,4),"","#0d1c42")+
    card("Jumlah Data Cocok",rows.length.toLocaleString("id-ID"),"","#7f8c8d");

  const x=rows.map(x=>x.datetime_utc);
  const got=rows.map(x=>num(x.tide_m_got410));
  const eot=rows.map(x=>num(x.tide_m_eot20));
  const dif=rows.map(x=>{
    const v=num(x.selisih_m);
    return v===null ? (num(x.tide_m_got410)-num(x.tide_m_eot20)) : v;
  });

  // Python asli menggunakan make_subplots(rows=2, cols=1):
  // panel atas = GOT4.10 vs EOT20, panel bawah = Selisih.
  // Implementasi di Plotly JS memakai dua pasangan sumbu dengan domain terpisah
  // agar hasil visual setara: tinggi 580 px, jarak vertikal 0.10, shared x-axis.
  Plotly.newPlot("validation-chart",[
    {
      x:x,y:got,type:"scatter",mode:"lines",name:"GOT4.10",
      xaxis:"x",yaxis:"y",
      line:{color:"#1f6f8b",width:2},
      hovertemplate:"<b>GOT4.10</b><br>Waktu: %{x}<br>Elevasi: %{y:.3f} m<extra></extra>"
    },
    {
      x:x,y:eot,type:"scatter",mode:"lines",name:"EOT20",
      xaxis:"x",yaxis:"y",
      line:{color:"#e08e2b",width:2,dash:"dash"},
      hovertemplate:"<b>EOT20</b><br>Waktu: %{x}<br>Elevasi: %{y:.3f} m<extra></extra>"
    },
    {
      x:x,y:dif,type:"scatter",mode:"lines",name:"Selisih",
      xaxis:"x2",yaxis:"y2",
      line:{color:"#8e44ad",width:1.5},
      fill:"tozeroy",
      fillcolor:"rgba(142,68,173,0.48)",
      hovertemplate:"Waktu: %{x}<br>Selisih: %{y:.3f} m<extra></extra>"
    }
  ],{
    title:{text:`Validasi Silang - ${st} - ${MONTH_ID[month]} ${year}`,x:0.02,xanchor:"left",font:{size:17,color:"#0D1C42"}},
    template:"plotly_white",
    height:580,
    hovermode:"x unified",
    margin:{l:70,r:70,t:105,b:75},
    paper_bgcolor:"white",
    plot_bgcolor:"white",
    font:{family:"Poppins, Arial, sans-serif",color:"#33415c"},

    // PANEL ATAS — Perbandingan GOT4.10 vs EOT20
    xaxis:{
      domain:[0,1],
      anchor:"y",
      showgrid:true,
      gridcolor:"#edf1f3",
      showticklabels:false,
      zeroline:false
    },
    yaxis:{
      domain:[0.38,0.91],
      title:"Elevasi terhadap MSL (m)",
      showgrid:true,
      gridcolor:"#edf1f3",
      zeroline:true,
      zerolinecolor:"#b7c4cc"
    },

    // PANEL BAWAH — Selisih GOT4.10 - EOT20
    xaxis2:{
      domain:[0,1],
      anchor:"y2",
      matches:"x",
      title:"Tanggal dan Waktu (UTC)",
      showgrid:true,
      gridcolor:"#edf1f3"
    },
    yaxis2:{
      domain:[0.06,0.27],
      title:"Selisih (m)",
      showgrid:true,
      gridcolor:"#edf1f3",
      zeroline:true,
      zerolinecolor:"#b7c4cc"
    },

    annotations:[
      {
        text:"Perbandingan GOT4.10 vs EOT20",
        x:0.5,y:0.98,xref:"paper",yref:"paper",
        showarrow:false,
        font:{size:15,color:"#0D1C42"}
      },
      {
        text:"Selisih (GOT4.10 - EOT20)",
        x:0.5,y:0.33,xref:"paper",yref:"paper",
        showarrow:false,
        font:{size:15,color:"#0D1C42"}
      }
    ],

    legend:{
      orientation:"h",
      yanchor:"bottom",
      y:1.08,
      xanchor:"right",
      x:1,
      bgcolor:"rgba(255,255,255,0.85)",
      bordercolor:"#dfe6e9",
      borderwidth:1,
      font:{size:11}
    }
  },{responsive:true,displaylogo:false});
}

function pinIcon(color, selected=false){
  const width = selected ? 34 : 26;
  const height = selected ? 46 : 36;
  const svg = `<svg width="${width}" height="${height}" viewBox="0 0 30 42" xmlns="http://www.w3.org/2000/svg"
      style="filter:drop-shadow(0 2px 2px rgba(0,0,0,.35))">
      <path d="M15 0C6.7 0 0 6.7 0 15c0 11.25 15 27 15 27s15-15.75 15-27C30 6.7 23.3 0 15 0z"
            fill="${color}" stroke="#fff" stroke-width="1.6"/>
      <circle cx="15" cy="15" r="6" fill="#fff"/>
    </svg>`;
  return L.divIcon({
    html:svg,className:"station-pin-icon",
    iconSize:[width,height],iconAnchor:[width/2,height],popupAnchor:[0,-height+4]
  });
}

function initMap(){
  const valid=stations.map(s=>({lat:num(s.latitude),lon:num(s.longitude)}))
    .filter(p=>p.lat!==null&&p.lon!==null);
  if(valid.length){
    mapHome=[
      valid.reduce((a,p)=>a+p.lat,0)/valid.length,
      valid.reduce((a,p)=>a+p.lon,0)/valid.length
    ];
  }
  map=L.map("station-map").setView(mapHome,mapZoom);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{
    attribution:"© OpenStreetMap contributors"
  }).addTo(map);
}

function updateMap(selected,focus=false){
  markers.forEach(m=>m.remove());
  markers=[];
  stations.forEach(s=>{
    const lat=num(s.latitude),lon=num(s.longitude);
    if(lat===null||lon===null)return;
    const selectedNow=s.station===selected;
    const color=selectedNow?"#c0392b":"#154360";
    const m=L.marker([lat,lon],{
      icon:pinIcon(color,selectedNow),
      title:s.station,
      riseOnHover:true
    }).addTo(map);
    m.bindTooltip(esc(s.station),{direction:"top",offset:[0,-4],opacity:.95});
    m.bindPopup(`<b>${esc(s.station)}</b><br>Lon: ${fmt(lon,6)}<br>Lat: ${fmt(lat,6)}`);
    markers.push(m);
  });
  if(focus){
    const target=stations.find(s=>s.station===selected);
    if(target){
      const lat=num(target.latitude),lon=num(target.longitude);
      if(lat!==null&&lon!==null) map.setView([lat,lon],11,{animate:true});
    }
  }
}
function resetMap(){
  map.setView(mapHome,mapZoom,{animate:true});
}
function detectExtrema(rows){
  const events=[];
  for(let i=1;i<rows.length-1;i++){
    const a=num(rows[i-1].tide_m),b=num(rows[i].tide_m),c=num(rows[i+1].tide_m);
    if([a,b,c].some(v=>v===null))continue;
    if(b>a&&b>=c)events.push({type:"Pasang",time:new Date(rows[i].datetime_wib),height:b});
    if(b<a&&b<=c)events.push({type:"Surut",time:new Date(rows[i].datetime_wib),height:b});
  }
  return events;
}
function updateDaily(){
  const st=document.getElementById("daily-station").value,date=document.getElementById("daily-date").value;
  if(!date)return;
  const start=new Date(date+"T00:00:00"),end=new Date(start);
  end.setDate(end.getDate()+1);
  const margin=3*3600*1000;
  const sdf=tide.filter(r=>r.station===st).map(r=>({...r,_d:new Date(r.datetime_wib)})).filter(r=>r._d>=new Date(start-margin)&&r._d<=new Date(end.getTime()+margin)).sort((a,b)=>a._d-b._d);
  const day=sdf.filter(r=>r._d>=start&&r._d<end);
  if(!day.length){document.getElementById("daily-summary").innerHTML=card("Status","-","Data tidak tersedia","#a8453a");Plotly.purge("daily-chart");document.getElementById("daily-events").innerHTML="";return}
  const validDay=day.filter(x=>Number.isFinite(num(x.tide_m)));
  const vals=validDay.map(x=>num(x.tide_m));
  const hi=Math.max(...vals), lo=Math.min(...vals);
  const events=detectExtrema(sdf).filter(e=>e.time>=start&&e.time<end);
  document.getElementById("daily-summary").innerHTML=card("Elevasi Tertinggi",fmt(hi),"m","#3f7d5a")+card("Elevasi Terendah",fmt(lo),"m","#a8453a")+card("Selisih Harian",fmt(hi-lo),"m","#2e4a8a")+card("Jumlah Pasang",events.filter(e=>e.type==="Pasang").length,"kali","#4a5578");
  const highs=events.filter(e=>e.type==="Pasang"), lows=events.filter(e=>e.type==="Surut");
  const traces=[{
    x:validDay.map(x=>x.datetime_wib),y:validDay.map(x=>num(x.tide_m)),type:"scatter",mode:"lines",name:"Prediksi Pasut",
    line:{color:"#2e4a8a",width:3,shape:"spline",smoothing:.8},
    fill:"tozeroy",fillcolor:"rgba(46,74,138,.10)"
  }];
  if(highs.length) traces.push({
    x:highs.map(e=>e.time),y:highs.map(e=>e.height),type:"scatter",mode:"markers+text",name:"Pasang",
    marker:{symbol:"triangle-up",size:13,color:"#3f7d5a",line:{color:"white",width:1.5}},
    text:highs.map(e=>e.time.toLocaleTimeString("id-ID",{hour:"2-digit",minute:"2-digit"})),
    textposition:"top center",textfont:{size:11,color:"#3f7d5a"}
  });
  if(lows.length) traces.push({
    x:lows.map(e=>e.time),y:lows.map(e=>e.height),type:"scatter",mode:"markers+text",name:"Surut",
    marker:{symbol:"triangle-down",size:13,color:"#a8453a",line:{color:"white",width:1.5}},
    text:lows.map(e=>e.time.toLocaleTimeString("id-ID",{hour:"2-digit",minute:"2-digit"})),
    textposition:"bottom center",textfont:{size:11,color:"#a8453a"}
  });
  Plotly.newPlot("daily-chart",traces,{
    title:{text:`Pasang Surut Harian - ${st} - ${date.split("-").reverse().join("/")}`,x:.02,xanchor:"left",font:{size:17,color:"#0D1C42"}},
    template:"plotly_white",height:420,
    xaxis:{title:"Jam (WIB)",range:[start,end],gridcolor:"#edf1f3",dtick:3*3600*1000,tickformat:"%H:%M"},
    yaxis:{title:"Elevasi terhadap MSL (m)",gridcolor:"#edf1f3",zeroline:false},
    hovermode:"x unified",margin:{l:65,r:25,t:80,b:60},
    legend:{orientation:"h",yanchor:"bottom",y:1.04,xanchor:"right",x:1,bgcolor:"rgba(255,255,255,.96)",bordercolor:"#d8e0e5",borderwidth:1},
    font:{family:"Poppins, Arial, sans-serif"}
  },{responsive:true,displaylogo:false});
  document.getElementById("daily-events").innerHTML=events.length?events.map(e=>{
    const high=e.type==="Pasang", color=high?"#3f7d5a":"#a8453a";
    const label=high?"Pasang tertinggi":"Surut terendah";
    const icon=high?"▲":"▼";
    return `<div class="pg-event" style="border-left:4px solid ${color}">
      <div class="pg-event-icon" style="background:${color}22;color:${color}">${icon}</div>
      <div class="pg-event-time">${e.time.toLocaleTimeString("id-ID",{hour:"2-digit",minute:"2-digit"})} WIB</div>
      <div class="pg-event-type" style="color:${color}">${label}</div>
      <div class="pg-event-height">${fmt(e.height)} m</div>
    </div>`;
  }).join(""):"<p class='muted'>Tidak ada puncak/lembah terdeteksi pada tanggal ini.</p>";
}
function updateBigMonths(){
  const st=document.getElementById("big-station").value;
  const months=[...new Set(bigIndex.filter(x=>x.station_code===st).map(x=>x.month))].filter(m=>MONTHS.includes(m));
  document.getElementById("big-month").innerHTML=months.map(m=>`<option value="${m}">${MONTH_ID[m]}</option>`).join("");
  if(months.length)renderBig();
}
function renderBig(){
  const st=document.getElementById("big-station").value,month=document.getElementById("big-month").value;
  const idx=bigIndex.find(x=>x.station_code===st&&x.month===month);
  if(!idx){document.getElementById("big-status").textContent="Data tidak tersedia.";return}
  fetch("data/validasi_big/"+idx.filename).then(r=>{if(!r.ok)throw new Error(`Tidak dapat membaca data BIG (HTTP ${r.status})`);return r.text()}).then(parseCSV).then(rows=>{
    const ms=bigMetrics.filter(x=>x.station===st&&x.month===month);
    const lookup=k=>{const x=ms.find(r=>r.perbandingan===k);return x||null};
    const a=lookup("GOT4.10 vs BIG"),b=lookup("EOT20 vs BIG"),c=lookup("GOT4.10 vs EOT20");
    const keys=[["RMSE (m)","rmse_m"],["MAE (m)","mae_m"],["Korelasi (r)","korelasi_r"],["Willmott's d","willmott_d"],["Jumlah Data","n_data"]];
    document.getElementById("big-table").innerHTML=`<thead><tr><th>Metrik</th><th>GOT4.10 vs BIG</th><th>EOT20 vs BIG</th><th>GOT4.10 vs EOT20</th></tr></thead><tbody>${keys.map(([l,k])=>`<tr><td>${l}</td><td>${k==="n_data"?(a?.[k]?Number(a[k]).toLocaleString("id-ID"):"-"):fmt(a?.[k],4)}</td><td>${k==="n_data"?(b?.[k]?Number(b[k]).toLocaleString("id-ID"):"-"):fmt(b?.[k],4)}</td><td>${k==="n_data"?(c?.[k]?Number(c[k]).toLocaleString("id-ID"):"-"):fmt(c?.[k],4)}</td></tr>`).join("")}</tbody>`;
    const sources=[["GOT4.10","tide_m_got410","#1f6f8b"],["EOT20","tide_m_eot20","#e08e2b"],["BIG","tide_m_big","#6c757d"]];
    Plotly.newPlot("big-bar-chart",sources.filter(s=>rows.some(r=>num(r[s[1]])!==null)).map(s=>({x:[s[0]],y:[rows.map(r=>num(r[s[1]])).filter(Number.isFinite).reduce((x,y)=>x+y,0)/rows.map(r=>num(r[s[1]])).filter(Number.isFinite).length],type:"bar",name:s[0],marker:{color:s[2]}})),{title:{text:"Rata-rata Elevasi Pasang Surut — GOT4.10, EOT20, dan BIG",x:.02,xanchor:"left",font:{size:17,color:"#0D1C42"}},template:"plotly_white",height:390,barmode:"group",margin:{l:65,r:25,t:95,b:65},paper_bgcolor:"white",plot_bgcolor:"white",font:{family:"Poppins, Arial, sans-serif",color:"#33415c"},xaxis:{title:"Sumber Data",showgrid:false},yaxis:{title:"Rata-rata Elevasi terhadap MSL (m)",gridcolor:"#edf1f3",zeroline:true,zerolinecolor:"#b7c4cc"},legend:{orientation:"h",yanchor:"bottom",y:1.08,xanchor:"right",x:1,bgcolor:"rgba(255,255,255,.96)",bordercolor:"#d8e0e5",borderwidth:1}},{responsive:true});
    Plotly.newPlot("big-line-chart",sources.filter(s=>rows.some(r=>num(r[s[1]])!==null)).map(s=>({x:rows.map(r=>r.datetime_utc),y:rows.map(r=>num(r[s[1]])),type:"scatter",mode:"lines",name:s[0],line:{color:s[2]}})),{title:{text:"Perbandingan Deret Waktu Pasang Surut — GOT4.10, EOT20, dan BIG",x:.02,xanchor:"left",font:{size:17,color:"#0D1C42"}},template:"plotly_white",height:520,margin:{l:65,r:25,t:95,b:70},xaxis:{title:"Tanggal dan Waktu (UTC)",gridcolor:"#edf1f3"},yaxis:{title:"Elevasi terhadap MSL (m)",gridcolor:"#edf1f3",zeroline:true,zerolinecolor:"#b7c4cc"},hovermode:"x unified",font:{family:"Poppins, Arial, sans-serif",color:"#33415c"},legend:{orientation:"h",yanchor:"bottom",y:1.05,xanchor:"right",x:1,bgcolor:"rgba(255,255,255,.96)",bordercolor:"#d8e0e5",borderwidth:1}},{responsive:true});
    document.getElementById("big-status").textContent=`${st} · ${MONTH_ID[month]} 2025`;
  }).catch(e=>{document.getElementById("big-status").textContent="Gagal membaca data validasi BIG: "+e.message;document.getElementById("big-status").className="status error"});
}

/* =====================================================================
   MODUL CETAK (bagian 2): keterangan stasiun + tombol Unduh PDF
   ===================================================================== */
function selText(id){
  const e=document.getElementById(id);
  return e&&e.options&&e.selectedIndex>=0?e.options[e.selectedIndex].text:"";
}
function fillPrintMeta(){
  const box=document.getElementById("print-meta");
  if(!box) return;
  const sEl=document.getElementById("station");
  const stName=selText("station"), stVal=sEl?sEl.value:"";
  const r=stations.find(x=>x.station===stName||x.station===stVal);
  let html=`Stasiun: <b>${esc(stName)}</b> &nbsp;|&nbsp; Tahun: <b>${esc(selText("year"))}</b> &nbsp;|&nbsp; Bulan: <b>${esc(selText("month"))}</b>`;
  if(r&&num(r.longitude)!==null&&num(r.latitude)!==null){
    html+=`<br>Koordinat Stasiun: Lon <b>${fmt(r.longitude,6)}</b>, Lat <b>${fmt(r.latitude,6)}</b>`;
  }
  box.innerHTML=html;
}
async function printReport(){
  const btn=document.getElementById("print-pdf");
  const label=btn.textContent;
  btn.disabled=true; btn.textContent="Menyiapkan…";
  try{ fillPrintMeta(); await ensurePrintImages(); }
  catch(e){ console.warn("Persiapan cetak:", e); }
  btn.disabled=false; btn.textContent=label;
  window.print();
}
window.addEventListener("beforeprint", fillPrintMeta);

async function init(){
  try{
    [tide,validation,metrics,stations,bigMetrics,bigIndex]=await Promise.all([csv(DATA.tide),csv(DATA.validation),csv(DATA.metrics),csv(DATA.stations),csv(DATA.bigMetrics),csv(DATA.bigIndex)]);
    setupSelectors();initMap();updateMap(document.getElementById("station").value,false);window.dashboardStations=stations;window.dispatchEvent(new Event("dashboard-ready"));updateDashboard();updateDaily();renderBig();
    document.querySelectorAll(".tab").forEach(btn=>btn.addEventListener("click",()=>{document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));document.querySelectorAll(".tab-panel").forEach(x=>x.classList.remove("active"));btn.classList.add("active");document.getElementById("tab-"+btn.dataset.tab).classList.add("active");setTimeout(()=>{map?.invalidateSize();window.dispatchEvent(new Event("resize"))},100)}));
    ["station","month","year"].forEach(id=>document.getElementById(id).addEventListener("change",updateDashboard));
    document.getElementById("map-home").addEventListener("click",resetMap);
    document.getElementById("daily-station").addEventListener("change",updateDaily);document.getElementById("daily-date").addEventListener("change",updateDaily);
    document.getElementById("big-station").addEventListener("change",updateBigMonths);document.getElementById("big-month").addEventListener("change",renderBig);
    document.getElementById("print-pdf").addEventListener("click",printReport);
  }catch(e){document.getElementById("status").textContent="Gagal memuat data: "+e.message+". Pastikan file CSV sudah ditempatkan sesuai struktur folder.";document.getElementById("status").className="status error";console.error(e)}
}
init();
