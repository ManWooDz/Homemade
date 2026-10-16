import { useRef, useState } from "react";
import { ChevronLeft, Star } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import RecipeContent from "../components/RecipeContent";
import { useLocale } from "../context/LocaleContext";

const RATING_TAGS = ["Delicious", "Great", "Tasty", "Not Bad", "Meh"];

export default function HistoryDetail({ item, onBack, activeTab, setActiveTab, onRateRecipe }) {
  const { t } = useLocale();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({ stars: 0, tag: null, feedback: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const savingRef = useRef(false);
  const discardDialogRef = useRef(null);
  const pendingLeaveRef = useRef(null);
  const dirty = editing && (draft.stars !== (item?.stars || 0) ||
    draft.tag !== (item?.tag || null) || draft.feedback !== (item?.feedback || ""));

  const leave = action => {
    if (savingRef.current) return;
    if (dirty) {
      pendingLeaveRef.current = action;
      discardDialogRef.current.showModal();
      return;
    }
    action();
  };

  const confirmLeave = () => {
    const action = pendingLeaveRef.current;
    pendingLeaveRef.current = null;
    discardDialogRef.current.close();
    action?.();
  };

  const startEditing = () => {
    setDraft({ stars: item.stars || 0, tag: item.tag || null, feedback: item.feedback || "" });
    setError("");
    setSaved(false);
    setEditing(true);
  };

  const saveRating = async event => {
    event.preventDefault();
    if (savingRef.current || draft.stars < 1 || draft.stars > 5 || draft.feedback.length > 240) return;
    savingRef.current = true;
    setSaving(true);
    setError("");
    try {
      const ok = await onRateRecipe(item.id, { ...draft, feedback: draft.feedback.trim() ? draft.feedback : null });
      if (!ok) {
        setError("บันทึกคะแนนไม่สำเร็จ ข้อมูลที่แก้ยังอยู่ กรุณาลองอีกครั้ง");
        return;
      }
      setEditing(false);
      setSaved(true);
    } catch {
      setError("บันทึกคะแนนไม่สำเร็จ ข้อมูลที่แก้ยังอยู่ กรุณาลองอีกครั้ง");
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  if (!item) {
    return null;
  }

  return (
    <div className="h-dvh bg-gray-100 flex justify-center font-sans overflow-hidden">
      <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl [&_button:focus-visible]:outline-2 [&_button:focus-visible]:outline-offset-2 [&_button:focus-visible]:outline-[#B93E25]">
        <div className="pt-8 px-6 flex items-center justify-center relative z-20 shrink-0 mb-4 bg-white">
          <button
            onClick={() => leave(onBack)}
            disabled={saving}
            aria-label={t("กลับ")}
            className="absolute left-6 w-11 h-11 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-md disabled:opacity-50"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
          <img src={logo} alt="HomeMade" className="h-18 object-contain" />
        </div>

        <div className="flex-1 overflow-y-auto px-6 pb-24 scrollbar-hide">
          <section aria-label={t("คะแนนของฉัน")} className="mb-6 border-b border-gray-200 pb-5">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">{t("คะแนนของฉัน")}</h2>
            {item.stars > 0 ? <>
              <div aria-label={t("{stars} ดาว", { stars: item.stars })} className="flex items-center gap-1 mb-2">
                {[1, 2, 3, 4, 5].map((n) => (
                  <Star
                    aria-hidden="true"
                    key={n}
                    className={`w-4 h-4 ${
                      n <= item.stars
                        ? "text-[#B93E25] fill-[#B93E25]"
                        : "text-gray-500"
                    }`}
                  />
                ))}
              </div>
              {item.tag && <p className="text-sm font-medium text-[#B93E25] mb-2">{t(item.tag)}</p>}
              {item.feedback && <p className="text-sm text-gray-700 whitespace-pre-wrap wrap-anywhere mb-3">{item.feedback}</p>}
            </> : <p className="text-sm text-gray-600 mb-3">{t("ยังไม่ให้คะแนน")}</p>}
            {saved && <p role="status" className="text-sm text-green-800 mb-3">{t("บันทึกคะแนนแล้ว")}</p>}
            {editing ? <form onSubmit={saveRating} aria-label={t("แก้ไขคะแนน")} aria-busy={saving}>
              <fieldset disabled={saving} className="mt-4 min-w-0">
                <legend className="text-sm font-medium text-gray-900">{t("เลือกคะแนน 1–5 ดาว")}</legend>
                <div className="flex gap-1 my-2">
                  {[1, 2, 3, 4, 5].map(stars => <button key={stars} type="button" autoFocus={stars === (draft.stars || 1)}
                    aria-label={t("ให้ {stars} ดาว", { stars })} aria-pressed={draft.stars === stars}
                    onClick={() => setDraft(previous => ({ ...previous, stars }))}
                    className="min-w-11 min-h-11 flex items-center justify-center rounded-lg disabled:opacity-50">
                    <Star aria-hidden="true" className={`w-7 h-7 ${stars <= draft.stars ? "text-[#B93E25] fill-[#B93E25]" : "text-gray-500"}`} />
                  </button>)}
                </div>
              </fieldset>
              <fieldset disabled={saving} className="min-w-0 mb-4">
                <legend className="text-sm font-medium text-gray-900 mb-2">{t("ความรู้สึกต่อเมนู (ไม่บังคับ)")}</legend>
                <div className="flex flex-wrap gap-2">
                  {RATING_TAGS.map(tag => <button key={tag} type="button" aria-pressed={draft.tag === tag}
                    onClick={() => setDraft(previous => ({ ...previous, tag: previous.tag === tag ? null : tag }))}
                    className={`min-h-11 px-3 rounded-full border text-sm font-medium disabled:opacity-50 ${draft.tag === tag ? "bg-[#B93E25] text-white border-[#B93E25]" : "border-gray-400 text-gray-700"}`}>{t(tag)}</button>)}
                </div>
              </fieldset>
              <label htmlFor="history-feedback" className="block text-sm font-medium text-gray-900 mb-2">{t("ความคิดเห็น (ไม่บังคับ)")}</label>
              <textarea id="history-feedback" value={draft.feedback} maxLength={240} disabled={saving}
                aria-describedby="history-feedback-count" rows={3}
                onChange={event => setDraft(previous => ({ ...previous, feedback: event.target.value }))}
                className="w-full rounded-xl border border-gray-400 p-3 text-gray-900 resize-y focus-visible:outline-2 focus-visible:outline-[#B93E25] disabled:opacity-50" />
              <p id="history-feedback-count" className="text-sm text-gray-600 text-right tabular-nums">{draft.feedback.length}/240</p>
              {error && <p role="alert" className="text-sm text-red-700 mt-2">{t(error)}</p>}
              <div className="flex gap-3 mt-4">
                <button type="submit" disabled={saving || draft.stars < 1 || draft.feedback.length > 240}
                  className="min-h-12 flex-1 rounded-full bg-[#B93E25] text-white font-semibold px-4 disabled:opacity-50">{t(saving ? "กำลังบันทึก..." : "บันทึกคะแนน")}</button>
                <button type="button" disabled={saving} onClick={() => leave(() => setEditing(false))}
                  className="min-h-12 rounded-full border border-gray-400 text-gray-700 px-5 font-medium disabled:opacity-50">{t("ยกเลิก")}</button>
              </div>
            </form> : <button type="button" onClick={startEditing}
              className="min-h-11 rounded-full border border-[#B93E25] text-[#B93E25] px-5 font-semibold">{t(item.stars > 0 ? "แก้ไขคะแนน" : "ให้คะแนนเมนูนี้")}</button>}
          </section>

          <RecipeContent recipe={item} />
        </div>

        <div inert={saving}>
          <BottomMenu activeTab={activeTab} setActiveTab={tab => leave(() => setActiveTab(tab))} />
        </div>
        <dialog ref={discardDialogRef} aria-labelledby="discard-rating-title"
          onCancel={() => { pendingLeaveRef.current = null; }}
          className="m-auto w-[calc(100%_-_2rem)] max-w-sm rounded-2xl bg-white p-5 text-gray-900 backdrop:bg-black/40">
          <h2 id="discard-rating-title" className="text-lg font-semibold mb-4">{t("ทิ้งการแก้ไขคะแนนที่ยังไม่ได้บันทึก?")}</h2>
          <div className="flex flex-wrap gap-3">
            <button type="button" autoFocus onClick={() => { pendingLeaveRef.current = null; discardDialogRef.current.close(); }}
              className="min-h-12 flex-1 rounded-full border border-gray-400 px-4 font-medium">{t("แก้ไขต่อ")}</button>
            <button type="button" onClick={confirmLeave}
              className="min-h-12 flex-1 rounded-full bg-[#B93E25] px-4 font-semibold text-white">{t("ทิ้งการแก้ไข")}</button>
          </div>
        </dialog>
      </div>
    </div>
  );
}
