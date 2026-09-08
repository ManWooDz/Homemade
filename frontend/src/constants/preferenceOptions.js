export const OTHER_OPTION = "อื่น ๆ";
export const NO_RESTRICTION = "ไม่มีข้อจำกัด";
export const EQUIPMENT_NONE = "ไม่มีอุปกรณ์พิเศษ";

export const CUISINE_OPTIONS = [
  "อาหารไทย",
  "อาหารเอเชีย",
  "อาหารตะวันตก",
  "อาหารรสจัด",
  "อาหารเพื่อสุขภาพ",
  "อาหาร Fast Food",
  "ของหวาน",
  "อาหารทำง่าย ๆ",
];

export const CUISINE_EMOJI = {
  "อาหารไทย": "🇹🇭",
  "อาหารเอเชีย": "🍜",
  "อาหารตะวันตก": "🍝",
  "อาหารรสจัด": "🌶️",
  "อาหารเพื่อสุขภาพ": "🥗",
  "อาหาร Fast Food": "🍔",
  "ของหวาน": "🍰",
  "อาหารทำง่าย ๆ": "🍳",
};

// Each item tagged isAllergy so CreateRecipe/Profile's narrower
// "อาการแพ้อาหาร" picker (feeds main.py's check_allergy(), which only
// understands true allergens) can filter out diet-type entries like
// Vegan/Halal without a separate label-mapping table.
const RESTRICTION_ITEMS = [
  { label: "แพ้ถั่ว", emoji: "🥜", isAllergy: true },
  { label: "แพ้นม / ผลิตภัณฑ์จากนม", emoji: "🥛", isAllergy: true },
  { label: "แพ้ไข่", emoji: "🥚", isAllergy: true },
  { label: "แพ้อาหารทะเล", emoji: "🦐", isAllergy: true },
  { label: "แพ้แป้งสาลี / Gluten", emoji: "🌾", isAllergy: true },
  { label: "แพ้ปลา", emoji: "🐟", isAllergy: true },
  { label: "แพ้ถั่วเหลือง", emoji: "🫘", isAllergy: true },
  { label: "แพ้งา", emoji: "🟤", isAllergy: true },
  { label: "ทาน Vegan", emoji: "🌱", isAllergy: false },
  { label: "ทานมังสวิรัติ", emoji: "🥦", isAllergy: false },
  { label: "ฮาลาล", emoji: "☪️", isAllergy: false },
];

export const RESTRICTION_OPTIONS = [
  NO_RESTRICTION,
  ...RESTRICTION_ITEMS.map((item) => item.label),
  OTHER_OPTION,
];

export const ALLERGY_OPTIONS = [
  NO_RESTRICTION,
  ...RESTRICTION_ITEMS.filter((item) => item.isAllergy).map((item) => item.label),
  OTHER_OPTION,
];

export const RESTRICTION_EMOJI = {
  [NO_RESTRICTION]: "✅",
  ...Object.fromEntries(RESTRICTION_ITEMS.map((item) => [item.label, item.emoji])),
  [OTHER_OPTION]: "✏️",
};

export const EQUIPMENT_OPTIONS = [
  EQUIPMENT_NONE,
  "กระทะ",
  "หม้อ",
  "หม้อหุงข้าว",
  "เตาไฟฟ้า",
  "เตาแก๊ส",
  "เตาอบ",
  "หม้อทอดไร้น้ำมัน",
  "ไมโครเวฟ",
  "เครื่องปั่น",
  "หม้อตุ๋น/สโลว์คุก",
  OTHER_OPTION,
];

export const EQUIPMENT_EMOJI = {
  [EQUIPMENT_NONE]: "🚫",
  "กระทะ": "🍳",
  "หม้อ": "🍲",
  "หม้อหุงข้าว": "🍚",
  "เตาไฟฟ้า": "🔌",
  "เตาแก๊ส": "🔥",
  "เตาอบ": "🥖",
  "หม้อทอดไร้น้ำมัน": "🍟",
  "ไมโครเวฟ": "⏱️",
  "เครื่องปั่น": "🥤",
  "หม้อตุ๋น/สโลว์คุก": "🍯",
  [OTHER_OPTION]: "✏️",
};

export const FREQUENCY_OPTIONS = [
  "แทบไม่เคย — 0 ครั้ง/สัปดาห์",
  "เมนู + ทำ — 1–2 ครั้ง/สัปดาห์",
  "ทำเป็นบางครั้ง — 3–4 ครั้ง/สัปดาห์",
  "ทำเป็นประจำ — 5–6 ครั้ง/สัปดาห์",
  "ทำอาหารทุกวัน — 7 ครั้งขึ้นไป/สัปดาห์",
];

export const FREQUENCY_EMOJI = {
  "แทบไม่เคย — 0 ครั้ง/สัปดาห์": "🚫",
  "เมนู + ทำ — 1–2 ครั้ง/สัปดาห์": "🙂",
  "ทำเป็นบางครั้ง — 3–4 ครั้ง/สัปดาห์": "👍",
  "ทำเป็นประจำ — 5–6 ครั้ง/สัปดาห์": "💪",
  "ทำอาหารทุกวัน — 7 ครั้งขึ้นไป/สัปดาห์": "🔥",
};

export const GOAL_OPTIONS = [
  "ประหยัดค่าอาหาร",
  "ใช้วัตถุดิบที่มีได้คุ้มค่า",
  "อยากฝึกทำอาหาร",
  "ทำอาหารเพื่อสุขภาพ",
  "อยากลองเมนูใหม่ ๆ",
  "ประหยัดเวลา",
];

export const GOAL_EMOJI = {
  "ประหยัดค่าอาหาร": "💰",
  "ใช้วัตถุดิบที่มีได้คุ้มค่า": "♻️",
  "อยากฝึกทำอาหาร": "👨‍🍳",
  "ทำอาหารเพื่อสุขภาพ": "🥗",
  "อยากลองเมนูใหม่ ๆ": "✨",
  "ประหยัดเวลา": "⏱️",
};

// Multi-select toggle where selecting `noneValue` clears every other
// selection, and selecting anything else clears `noneValue`. Pure
// function — caller does setState(toggleInList(current, option, none)).
export const toggleInList = (list, option, noneValue) => {
  if (option === noneValue) {
    return list.includes(noneValue) ? [] : [noneValue];
  }
  if (list.includes(option)) {
    return list.filter((item) => item !== option);
  }
  return [...list.filter((item) => item !== noneValue), option];
};
