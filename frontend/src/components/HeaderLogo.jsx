import logo from "../assets/HomeMade_Logo.png";

export default function HeaderLogo() {
  return (
    <div className="w-full flex justify-center items-center">
      <img src={logo} alt="HomeMade" className="h-18 object-contain" />
    </div>
  );
}
