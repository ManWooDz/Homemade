import { useState } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../assets/HomeMade_Logo.png";
import BackButton from "../components/BackButton";
import HeaderLogo from "../components/HeaderLogo";

export default function InputPassword() {
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const navigate = useNavigate();

  const handleResetPassword = (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      alert("รหัสผ่านไม่ตรงกัน");
      return;
    }

    alert("เปลี่ยนรหัสผ่านสำเร็จ");
    navigate("/login");
  };

  return (
    <div className="w-full h-full px-8 pt-6 pb-10 bg-background-primary flex flex-col justify-start items-center overflow-hidden">
      {/* Top Header: Logo */}
      <HeaderLogo />

      {/* Back Button Container */}
      <div className="w-full flex justify-start items-center ">
        <BackButton to="/input-otp" />
      </div>

      {/* Form Section */}
      <form
        onSubmit={handleResetPassword}
        className="w-full flex flex-col justify-start items-center mt-24"
      >
        {/* Title */}
        <h1 className="w-full text-h2 font-semibold text-text-black text-left mb-4">
          Reset Password
        </h1>

        {/* Input Fields */}
        <div className="w-full flex flex-col justify-start items-center gap-4.25">
          <input
            type="password"
            placeholder="New Password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full h-11 px-4 bg-background-primary rounded-full border border-stroke-text-field text-body-large text-text-black placeholder:text-text-neutral focus:outline-none focus:border-stroke-brands"
            required
          />

          <input
            type="password"
            placeholder="Confirm password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full h-11 px-4 bg-background-primary rounded-full border border-stroke-text-field text-body-large text-text-black placeholder:text-text-neutral focus:outline-none focus:border-stroke-brands"
            required
          />
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          className="w-full h-11 mt-24.5 bg-button-primary hover:opacity-95 text-button-neutral text-body-medium font-semibold rounded-full flex justify-center items-center transition-all cursor-pointer"
        >
          ยืนยัน
        </button>
      </form>
    </div>
  );
}
