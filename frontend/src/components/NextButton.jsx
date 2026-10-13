import { useLocale } from "../context/LocaleContext";
import { ChevronRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function NextButton({ to, onClick }) {
    const { t } = useLocale();
  const navigate = useNavigate();

  const handleNext = () => {
    if (onClick) {
      onClick();
    } else {
      navigate(to);
    }
  };

  return (
    <button
      type="button"
      onClick={handleNext}
      aria-label={t("Next")}
      className="w-14 h-14 bg-button-primary text-text-white rounded-full flex items-center justify-center shadow-md cursor-pointer"
    >
      <ChevronRight className="w-7 h-7" />
    </button>
  );
}
