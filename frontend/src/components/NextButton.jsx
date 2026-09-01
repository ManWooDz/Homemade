import { ChevronRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function NextButton({ to, onClick }) {
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
      aria-label="Next"
      className="w-9 h-9 bg-button-primary text-text-white rounded-full flex items-center justify-center shadow-md cursor-pointer"
    >
      <ChevronRight className="w-5 h-5" />
    </button>
  );
}
