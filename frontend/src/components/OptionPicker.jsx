export function OptionChips({ options, selected, multiple, onToggle, emojiMap }) {
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
            onClick={() => onToggle(option)}
            className={`h-11 px-5 rounded-full border flex justify-center items-center text-body-large transition-all cursor-pointer ${
              isSelected
                ? "bg-button-primary border-button-primary text-text-white font-normal"
                : "bg-button-neutral border-border-stroke-btn-tertiary text-text-tertiary font-normal hover:bg-background-tertiary"
            }`}
          >
            {emojiMap?.[option] && <span className="mr-1.5">{emojiMap[option]}</span>}
            {option}
          </button>
        );
      })}
    </div>
  );
}

export function OptionList({ options, selected, multiple, onToggle, emojiMap }) {
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
            onClick={() => onToggle(option)}
            className={`w-full h-14 pl-3.5 pr-7 py-2 rounded-2xl flex items-center transition-all cursor-pointer ${
              isSelected
                ? "bg-button-secondary border border-border-stroke-brands shadow-[0px_0px_4px_0px_rgba(0,0,0,0.25)] text-text-black"
                : "bg-background-primary border border-border-stroke-btn-tertiary text-text-tertiary hover:bg-background-tertiary"
            }`}
          >
            <span className="text-body-medium font-normal truncate">
              {emojiMap?.[option] && <span className="mr-1.5">{emojiMap[option]}</span>}
              {option}
            </span>
          </button>
        );
      })}
    </div>
  );
}
