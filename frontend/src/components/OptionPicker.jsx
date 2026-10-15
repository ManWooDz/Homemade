import { useLocale } from "../context/LocaleContext";
export function OptionChips({ options, selected, multiple, onToggle, emojiMap }) {
    const { t } = useLocale();
  return (
    <div className="w-full flex justify-center items-center gap-2 flex-wrap max-w-[358px]">
      {options.map((option) => {
        const isSelected = multiple
          ? selected.includes(option)
          : selected === option;
        return (
          <button
            key={option}
            type="button"
            aria-pressed={isSelected}
            onClick={() => onToggle(option)}
            className={`min-h-11 max-w-full px-5 py-2 rounded-full border flex justify-center items-center text-body-large transition-colors cursor-pointer ${
              isSelected
                ? "bg-button-primary border-button-primary text-text-white font-normal"
                : "bg-button-neutral border-border-stroke-btn-tertiary text-text-tertiary font-normal hover:bg-background-tertiary"
            }`}
          >
            {emojiMap?.[option] && <span aria-hidden="true" className="mr-1.5">{emojiMap[option]}</span>}
            {t(option)}
          </button>
        );
      })}
    </div>
  );
}

export function OptionList({ options, selected, multiple, onToggle, emojiMap }) {
    const { t } = useLocale();
  return (
    <div className="w-full flex flex-col gap-2.5 max-w-[358px]">
      {options.map((option) => {
        const isSelected = multiple
          ? selected.includes(option)
          : selected === option;
        return (
          <button
            key={option}
            type="button"
            aria-pressed={isSelected}
            onClick={() => onToggle(option)}
            className={`w-full min-h-14 px-4 py-3 rounded-2xl flex items-center text-left transition-colors cursor-pointer ${
              isSelected
                ? "bg-button-secondary border border-border-stroke-brands text-text-black"
                : "bg-background-primary border border-border-stroke-btn-tertiary text-text-tertiary hover:bg-background-tertiary"
            }`}
          >
            <span className="text-body-medium font-normal">
              {emojiMap?.[option] && <span aria-hidden="true" className="mr-1.5">{emojiMap[option]}</span>}
              {t(option)}
            </span>
          </button>
        );
      })}
    </div>
  );
}
