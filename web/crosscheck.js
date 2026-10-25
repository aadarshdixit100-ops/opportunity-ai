const fs=require('fs'), path=require('path');
globalThis.OPP_TODAY='2026-10-25';
const E=require('./engine.js');
// works whether web/ sits inside the project or beside it
function dataDir(){
  const cands=[path.join(__dirname,'..','data'), path.join(__dirname,'..','opportunity-ai','data')];
  for(const c of cands) if(fs.existsSync(path.join(c,'opportunities.json'))) return c;
  throw new Error('could not find data/ next to '+__dirname);
}
const DD=dataDir();
const opps=JSON.parse(fs.readFileSync(path.join(DD,'opportunities.json'),'utf8')).opportunities;
const K=JSON.parse(fs.readFileSync(path.join(DD,'knowledge.json'),'utf8'));
const refPath=path.join(__dirname,'py_ref.json');
if(!fs.existsSync(refPath)){
  console.log('missing web/py_ref.json — run:  python3 web/make_reference.py');
  process.exit(2);
}
const ref=JSON.parse(fs.readFileSync(refPath,'utf8'));
const demo={name:"Aarav",degree:"B.Tech",branch:"Chemical Engineering",year:2,cgpa:8.2,
 skills:["Python","Pandas","Excel","Thermodynamics","Git","SQL","Data Visualization"],
 interests:["Data Science","Machine Learning","Chemical Engineering","Research"],
 work_mode:"Any",location:"Any",experience:"Beginner",gender:"Prefer not to say"};
const t=E.today();
let fails=0, maxd=0;
function chk(label,js,py){
  if(typeof js==='number'&&typeof py==='number'){ const d=Math.abs(js-py); if(d>maxd)maxd=d;
    if(d>0.05){ console.log(`  MISMATCH ${label}: js=${js} py=${py} d=${d.toFixed(3)}`); fails++; } return; }
  if(String(js)!==String(py)){ console.log(`  MISMATCH ${label}: js=${js} py=${py}`); fails++; }
}
opps.forEach(o=>{
  chk(`fit ${o.id}`, E.scoreOpportunity(demo,o,E.DEFAULT_WEIGHTS,K.skill_synonyms).score_pct, ref.fits[o.id]);
  chk(`elig ${o.id}`, E.evaluateEligibility(demo,o,t).status, ref.elig[o.id]);
  chk(`timing ${o.id}`, E.timingStatus(o,t,true), ref.timing[o.id]);
});
const radar=E.buildRadar(demo,opps,E.DEFAULT_WEIGHTS,t,true,K);
['apply_now','prepare_for','explore','excluded'].forEach(p=>{
  chk(`pane ${p}`, radar[p].map(i=>i.opportunity.id).join(','), ref.panes[p].join(','));
});
const acts=E.actionPriority(demo,opps,E.DEFAULT_WEIGHTS,t,K,true,5);
console.log('js actions:', acts.map(a=>`${a.skill}:${a.priority}`).join(' | '));
ref.actions.forEach((ra,i)=>{
  if(!acts[i]){ console.log(`  MISSING action ${ra.skill}`); fails++; return; }
  chk(`action ${i} skill`, acts[i].skill, ra.skill);
  chk(`action ${i} priority`, acts[i].priority, ra.priority);
  chk(`action ${i} hours`, acts[i].hours, ra.hours);
  chk(`action ${i} gap`, acts[i].gap, ra.gap);
});
const resume=`Aarav Sharma
Email: aarav@example.com

Skills
Python, SQL, Excel, Git

Projects
Built a sales dashboard using Python and SQL that cut reporting time by half.
`;
const o1=opps.find(o=>o.id==='OPP001');
E.evidenceMatrix(resume,o1,K.skill_synonyms).forEach((r,i)=>{
  chk(`evidence ${i} label`, r.label, ref.evidence[i].label);
  chk(`evidence ${i} section`, r.section, ref.evidence[i].section);
});
console.log(`\nfuzzy check: python/pytorch=${E.tokenSetRatio('python','pytorch').toFixed(1)} (py 61.5)`);
console.log(`\nmax fit delta: ${maxd.toFixed(4)} | mismatches: ${fails}`);
process.exit(fails?1:0);
