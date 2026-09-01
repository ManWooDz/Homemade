import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import logo from "../assets/HomeMade_Logo.png";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    navigate("/home");
  };

  return (
    <div className="w-full h-full px-6 bg-background-primary flex flex-col justify-center items-center overflow-hidden">
      <div className="w-full h-auto flex flex-col justify-start items-center gap-8">
        {/* Logo - แก้คลาสความกว้างเป็น w-[173px] */}
        <img
          src={logo}
          alt="HomeMade Logo"
          className="w-[173px] h-auto object-contain"
        />

        {/* Form Container */}
        <form
          onSubmit={handleLogin}
          className="w-full h-auto flex flex-col justify-start items-center gap-4"
        >
          {/* Inputs Section */}
          <div className="w-full h-auto flex flex-col justify-start items-center gap-3">
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
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="w-full h-11 mt-2 bg-button-primary hover:opacity-95 text-button-neutral text-body-medium font-semibold rounded-full flex justify-center items-center transition-all cursor-pointer"
          >
            Login
          </button>

          {/* Links Footer */}
          <div className="w-full flex justify-center items-center gap-2 text-caption mt-1">
            <Link
              to="/register"
              className="text-text-brands font-normal hover:underline"
            >
              Sign in
            </Link>
            <div className="w-px h-3 bg-text-black"></div>
            <Link
              to="/reset-password"
              className="text-text-black font-normal hover:underline"
            >
              Forgot password?
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
