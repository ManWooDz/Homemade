import { useState } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../assets/HomeMade_Logo.png";
import BackButton from "../components/BackButton";
import HeaderLogo from "../components/HeaderLogo";

export default function ResetPassword() {
  const [phoneNumber, setPhoneNumber] = useState("");
  const navigate = useNavigate();

  const handleSendOTP = (e) => {
    e.preventDefault();
    if (!phoneNumber) return;

    // Navigate to Input Password screen
    navigate("/input-OTP");
  };

  return (
    <div className="w-full h-full px-8 pt-6 pb-10 bg-background-primary flex flex-col justify-start items-center overflow-hidden">
      {/* Top Header: Logo */}
      <HeaderLogo />

      {/* Back Button Container */}
      <div className="w-full flex justify-start items-center">
        <BackButton to="/login" />
      </div>

      {/* Form Section */}
      <form
        onSubmit={handleSendOTP}
        className="w-full flex flex-col justify-start items-center mt-24"
      >
        {/* Title */}
        <h1 className="w-full text-h2 font-semibold text-text-black text-left mb-4">
          Reset Password
        </h1>

        {/* Input Phone Number */}
        <div className="w-full flex flex-col justify-start items-center">
          <input
            type="tel"
            placeholder="Phone number"
            value={phoneNumber}
            onChange={(e) => setPhoneNumber(e.target.value)}
            className="w-full h-11 px-4 bg-background-primary rounded-full border border-stroke-text-field text-body-large text-text-black placeholder:text-text-neutral focus:outline-none focus:border-stroke-brands"
            required
          />
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          className="w-full h-11 mt-24.5 bg-button-primary hover:opacity-95 text-button-neutral text-body-medium font-semibold rounded-full flex justify-center items-center transition-all cursor-pointer"
        >
          รับ OTP
        </button>
      </form>
    </div>
  );
}
