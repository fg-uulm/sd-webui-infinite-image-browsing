import{d as S,a2 as $,aL as g,dj as b,r as w,V as p,W as d,X as a,c as r,a4 as i,Y as u,Z as n,$ as B,a9 as I,a5 as m,x as V,y as _,z as v,ak as W,al as D,dk as L,a1 as N}from"./index-58aa78ac.js";/* empty css              */const R={class:"container"},F={class:"actions"},j={class:"uni-desc"},q={class:"snapshot"},z=S({__name:"index",props:{tabIdx:{},paneIdx:{},id:{},paneKey:{}},setup(A){const h=$(),t=g(),k=e=>{h.tabList=V(e.tabs)},f=b(async e=>{await L(`workspace_snapshot_${e.id}`),t.snapshots=t.snapshots.filter(c=>c.id!==e.id),_.success(v("deleteSuccess"))}),o=w(""),y=async()=>{if(!o.value){_.error(v("nameRequired"));return}const e=t.createSnapshot(o.value);await t.addSnapshot(e),_.success(v("saveCompleted"))};return(e,c)=>{const C=W,l=D;return p(),d("div",R,[a("div",F,[r(C,{value:o.value,"onUpdate:value":c[0]||(c[0]=s=>o.value=s),placeholder:e.$t("name"),style:{"max-width":"300px"}},null,8,["value","placeholder"]),r(l,{type:"primary",onClick:y},{default:i(()=>[u(n(e.$t("saveWorkspaceSnapshot")),1)]),_:1})]),a("p",j,n(e.$t("WorkspaceSnapshotDesc")),1),a("ul",q,[(p(!0),d(B,null,I(m(t).snapshots,s=>(p(),d("li",{key:s.id},[a("div",null,[a("span",null,n(s.name),1)]),a("div",null,[r(l,{onClick:x=>k(s)},{default:i(()=>[u(n(e.$t("restore")),1)]),_:2},1032,["onClick"]),r(l,{onClick:x=>m(f)(s)},{default:i(()=>[u(n(e.$t("remove")),1)]),_:2},1032,["onClick"])])]))),128))])])}}});const K=N(z,[["__scopeId","data-v-2c44013c"]]);export{K as default};
