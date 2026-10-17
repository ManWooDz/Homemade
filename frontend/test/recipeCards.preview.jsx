
// Development-only: synthetic recipes and intercepted requests; no real account or generation.
import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import RecipeDetail from '../src/pages/RecipeDetail.jsx';
import CookingPage from '../src/pages/CookingPage.jsx';
import {AuthProvider} from '../src/context/AuthContext.jsx';
import {LocaleProvider} from '../src/context/LocaleContext.jsx';
import '../src/index.css';
const params = new URLSearchParams(location.search);
const locale = params.get('locale') === 'en' ? 'en' : 'th';
window.fetch = async input => {
  const path = new URL(typeof input === 'string' ? input : input.url, location.origin).pathname;
  if (path === '/api/auth/me') return Response.json({status:'success',data:{id:1,locale}});
  throw new Error('Unexpected request blocked by recipe card QA: '+path);
};
const image = '/src/assets/HomeMade_Logo.png';
const instructions = params.has('plain') ? [
  '1. Cook quinoa according to package.',
  '2. Massage kale with olive oil and lemon juice.',
  '3. Chop avocado and tomatoes.',
  '4. Combine all ingredients in a bowl.',
  '5. Top with pumpkin seeds and desired dressing.',
] : locale === 'th' ? [
  '1. เตรียมผัก\nล้างผักทุกชนิดให้สะอาด จากนั้นหั่นตามขนาดที่กำหนดไว้ และพักให้สะเด็ดน้ำ',
  '2. ลวกผัก\nต้มน้ำให้เดือด ใส่เกลือเล็กน้อย ลวกผักแต่ละชนิดให้พอสุก แล้วพักให้เย็น',
  '3. คั่วเมล็ดทานตะวัน\nตั้งกระทะให้ร้อนปานกลาง คั่วเมล็ดทานตะวันโดยไม่ใส่น้ำมันจนเริ่มหอม',
  '4. จัดจาน\nนำผักที่เตรียมแล้วมาจัดจาน ราดน้ำมันมะกอกและปรุงรสตามชอบ',
  '5. เสิร์ฟ\nเสิร์ฟทันทีขณะที่ผักยังกรอบ และตรวจสอบวัตถุดิบก่อนรับประทาน',
] : ['1. Prepare the vegetables\nWash and cut the vegetables into bite-sized pieces.', '2. Blanch\nBlanch in boiling water, then drain.', '3. Toast the seeds\nToast in a dry pan until fragrant.', '4. Plate\nArrange the vegetables and add the dressing.', '5. Serve\nServe while the vegetables are crisp.'];
const nutrition = {basis:'per_serving',calories:320,carbs_g:42,protein_g:12,fat_g:8,fiber_g:6,sugar_g:5,sodium_mg:180,vitamin_c_mg:45};
const base = {id:1,name:params.has('long') ? 'Superfood Veggie Bowl — เมนูผักหลากสีที่มีชื่อยาวสำหรับตรวจสอบการตัดบรรทัด' : 'Superfood Veggie Bowl',image,ratings:4.8,review:72,
  estimated_total_time:{min_minutes:15,max_minutes:20},tags:['Healthy / Diet','Quick & Easy'],
  short_description:locale==='th'?'โบลผักสุขภาพที่รวมซูเปอร์ฟู้ดหลายชนิด':'A colourful bowl of vegetables and toasted seeds.',
  ingredients:['Green Oak','Tomatoes','Purple cabbage'].map(name=>({name,image})),instructions,
  nutrition,computed_nutrition:nutrition,nutrition_partially_estimated:false};
if(params.has('missing'))Object.assign(base,{nutrition:null,computed_nutrition:null,nutrition_origin:'base_calculation',nutrition_partially_estimated:true});
const generated = {...base,_historyId:1,recipe_name:base.name,servings:2,usage_time:locale==='th'?'15–20 นาที':'15–20 min',diet_tags:base.tags,
  adjusted_ingredients:locale==='th'?['กรีนโอ๊ค 200 กรัม','มะเขือเทศ 300 กรัม','กะหล่ำม่วง 150 กรัม']:['Green Oak 200 g','Tomatoes 300 g','Purple cabbage 150 g'],safety_warning:'ตรวจสอบอาหารที่แพ้ก่อนรับประทาน'};
export default function Preview(){
  const [receipt,setReceipt]=useState('');
  const [favorite,setFavorite]=useState(false);
  const [mode,setMode]=useState(params.get('view')||'detail');
  const common={recipe:base,onBack:()=>setReceipt('back'),activeTab:'cooking',setActiveTab:tab=>setReceipt('nav:'+tab)};
  return <><output className="sr-only">{receipt}</output>{mode==='detail'?<RecipeDetail {...common} isFavorite={favorite} onToggleFavorite={()=>setFavorite(v=>!v)} onConfirm={selected=>{setReceipt('selected:'+selected.map(i=>i.name).join(','));setMode('cooking')}}/>:<CookingPage {...common} generatedRecipe={generated} isCustom={mode==='custom'} historyItem={{id:1,is_favorite:favorite}} onToggleFavorite={()=>setFavorite(v=>!v)} onRateRecipe={async()=>{setReceipt('rated');return true}}/>}</>;
}
createRoot(document.getElementById('root')).render(<AuthProvider><LocaleProvider><Preview/></LocaleProvider></AuthProvider>);
