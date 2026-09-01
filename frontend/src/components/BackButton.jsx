import { ChevronLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function BackButton({ to, onClick }) {
  const navigate = useNavigate();

  const handleBack = () => {
    if (onClick) {
      onClick();
      return;
    }
    if (window.history.state?.idx > 0) {
      navigate(-1);
    } else {
      navigate(to);
    }
  };

  return (
    <button
      type="button"
      onClick={handleBack}
      aria-label="Back"
      className="w-9 h-9 bg-button-primary text-text-white rounded-full flex items-center justify-center shadow-md cursor-pointer"
    >
      <ChevronLeft className="w-5 h-5" />
    </button>
  );
}
