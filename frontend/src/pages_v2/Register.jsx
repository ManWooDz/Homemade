import { useState } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../assets/HomeMade_Logo.png";
import BackButton from "../components/BackButton";
import HeaderLogo from "../components/HeaderLogo";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const navigate = useNavigate();

  const handleRegister = (e) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      alert("Password ไม่ตรงกัน");
      return;
    }
    navigate("/quiz-step-1");
  };

  return (
    <div className="w-full h-full px-8 pt-6 pb-10 bg-background-primary flex flex-col justify-start items-center overflow-hidden">
      {/* Top Header: Logo */}
      <HeaderLogo />

      {/* Back Button Container */}
      <div className="w-full flex justify-start items-center ">
        <BackButton to="/login" />
      </div>

      {/* Form Section */}
      <form
        onSubmit={handleRegister}
        className="w-full flex flex-col justify-start items-center mt-24"
      >
        {/* Title Sign In */}
        <h1 className="text-h2 font-semibold text-text-black text-center mb-4">
          Sign In
        </h1>

        {/* Input Fields Container (ระยะห่างระหว่างช่อง 17px ตาม top Figma) */}
        <div className="w-full flex flex-col justify-start items-center gap-4.25">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full h-11 px-4 bg-background-primary rounded-full border border-stroke-text-field text-body-large text-text-black placeholder:text-text-neutral focus:outline-none focus:border-stroke-brands"
            required
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
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

        {/* Submit Button (วางห่างจาก Confirm Password 98px ตามระยะ top-[568px] - top-[470px]) */}
        <button
          type="submit"
          className="w-full h-11 mt-24.5 bg-button-primary hover:opacity-95 text-button-neutral text-body-medium font-semibold rounded-full flex justify-center items-center transition-all cursor-pointer"
        >
          Sign In
        </button>
      </form>
    </div>
  );
}
