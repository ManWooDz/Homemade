import logo from "../assets/HomeMade_Logo.png";

export default function HeaderLogo({ size = "h-18" }) {
  return (
    <div className="w-full flex justify-center items-center">
      <img src={logo} alt="HomeMade" className={`${size} object-contain`} />
    </div>
  );
}
