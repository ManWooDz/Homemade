import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../assets/HomeMade_Logo.png";
import BackButton from "../components/BackButton";
import HeaderLogo from "../components/HeaderLogo";

export default function InputOTP() {
  const [otp, setOtp] = useState(["", "", "", ""]);
  const inputRefs = useRef([]);
  const navigate = useNavigate();

  // จัดการการพิมพ์ OTP ให้เลื่อนไปช่องถัดไปอัตโนมัติ
  const handleOtpChange = (index, value) => {
    if (isNaN(value)) return;
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    if (value !== "" && index < 3) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handleVerify = (e) => {
    e.preventDefault();
    // Verify OTP -> Navigate back to Login or Next step
    navigate("/input-password");
  };

  return (
    <div className="w-full h-full px-8 pt-6 pb-10 bg-background-primary flex flex-col justify-start items-center overflow-hidden">
      {/* Top Header: Logo */}
      <HeaderLogo />

      {/* Back Button Container */}
      <div className="w-full flex justify-start items-center">
        <BackButton to="/reset-password" />
      </div>

      {/* Form Section */}
      <form
        onSubmit={handleVerify}
        className="w-full flex flex-col justify-start items-center mt-24"
      >
        {/* Title */}
        <h1 className="w-full text-h2 font-semibold text-text-black text-left mb-4">
          ใส่รหัส OTP
        </h1>

        {/* OTP Input Fields & Resend Button */}
        <div className="w-full flex justify-between items-center gap-3">
          <div className="flex gap-2">
            {otp.map((digit, index) => (
              <input
                key={index}
                ref={(el) => (inputRefs.current[index] = el)}
                type="text"
                maxLength={1}
                value={digit}
                onChange={(e) => handleOtpChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                className="w-10 h-11 bg-forms-otp-fill-default text-center text-body-large text-text-black rounded-lg focus:outline-none focus:bg-forms-otp-fill-filled focus:border focus:border-stroke-brands"
              />
            ))}
          </div>

          {/* Resend Button */}
          <button
            type="button"
            className="h-11 px-4 bg-button-neutral rounded-full border border-stroke-brands text-text-brands text-body-medium font-normal flex justify-center items-center whitespace-nowrap cursor-pointer hover:bg-gray-50 transition-colors"
          >
            ส่งอีกครั้ง
          </button>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          className="w-full h-11 mt-24 bg-button-primary hover:opacity-95 text-button-neutral text-body-medium font-semibold rounded-full flex justify-center items-center transition-all cursor-pointer"
        >
          ยืนยัน
        </button>
      </form>
    </div>
  );
}
