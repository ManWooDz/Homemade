import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
const bundle = await build({
    stdin: {
        contents: 'export { default as Editor } from "./src/components/ProfileEditor.jsx"; export { default as Cropper } from "./src/components/AvatarCropper.jsx"; export { setLocale } from "./src/context/LocaleContext";',
        resolveDir: fileURLToPath(new URL("../", import.meta.url)), loader: "jsx",
    },
    bundle: true, write: false, platform: "node", format: "cjs", packages: "external", jsx: "automatic",
    plugins: [{ name: "test-context", setup(build) {
        build.onResolve({ filter: /^react-easy-crop$/ }, () => ({ path: "cropper", namespace: "test-cropper" }));
        build.onLoad({ filter: /.*/, namespace: "test-cropper" }, () => ({ contents: 'import {createElement} from "react"; export default function Cropper(props){return createElement("div",{...props.cropperProps,"data-crop-shape":props.cropShape,"data-keyboard-step":props.keyboardStep})}', resolveDir: fileURLToPath(new URL("../", import.meta.url)) }));
        build.onResolve({ filter: /\/context\/AuthContext$/ }, () => ({ path: "auth", namespace: "test-auth" }));
        build.onLoad({ filter: /.*/, namespace: "test-auth" }, () => ({ contents: 'export function useAuth(){return {user:{display_name:"เชฟ <script>"},updateProfile:async()=>({success:true})}}' }));
        build.onResolve({ filter: /\/context\/LocaleContext$/ }, () => ({ path: "locale", namespace: "test-locale" }));
        build.onLoad({ filter: /.*/, namespace: "test-locale" }, () => ({
            contents: 'import {translate} from "./translations.js"; let locale="th"; export function setLocale(value){locale=value} export function useLocale(){return {t:(text,values)=>translate(text,locale,values)}}',
            resolveDir: fileURLToPath(new URL("../src/utils/", import.meta.url)),
        }));
    } }],
});
const compiled = { exports: {} };
new Function("require", "module", "exports", bundle.outputFiles[0].text)(require, compiled, compiled.exports);
const { Editor, Cropper, setLocale } = compiled.exports;

for (const [locale, title, choose, defaultPicture, zoom, confirm] of [
    ["th", "แก้ไขโปรไฟล์", "เลือกรูป", "ใช้รูปเริ่มต้น", "ซูม", "ใช้รูปนี้"],
    ["en", "Edit profile", "Choose picture", "Use default picture", "Zoom", "Confirm crop"],
]) {
    for (const hasPicture of [false, true]) {
        test(`profile editor labels and picture actions remain accessible (${locale}, picture=${hasPicture})`, () => {
            setLocale(locale);
            const html = renderToStaticMarkup(createElement(Editor, { avatarUrl: hasPicture ? "/avatar.jpg" : "" }));
            assert.ok(html.includes(title));
            assert.ok(html.includes(choose));
            assert.ok(html.includes(defaultPicture));
            assert.match(html, /aria-labelledby="profile-picture-heading"/);
            assert.match(html, /id="profile-name"[^>]*aria-describedby="profile-name-help"/);
            assert.match(html, /type="file"[^>]*accept="image\/jpeg,image\/png,image\/webp"[^>]*hidden=""/);
            assert.ok(html.includes("เชฟ &lt;script&gt;"));
            assert.doesNotMatch(html, /<script>/);
            const defaultButton = html.match(new RegExp(`<button[^>]*>[\\s\\S]*?${defaultPicture}</button>`, "g"))?.at(-1);
            assert.ok(defaultButton);
            assert.equal(/disabled=""/.test(defaultButton), !hasPicture);
        });
    }
    test(`cropper retains circular, keyboard and zoom controls before the picture is ready (${locale})`, () => {
        setLocale(locale);
        const html = renderToStaticMarkup(createElement(Cropper, { source: "/avatar.jpg" }));
        assert.match(html, /aria-labelledby="avatar-crop-heading"/);
        assert.match(html, /aria-describedby="crop-help"/);
        assert.match(html, /data-crop-shape="round"/);
        assert.match(html, /data-keyboard-step="10"/);
        assert.match(html, /type="range"[^>]*min="1"[^>]*max="3"[^>]*step="0.05"[^>]*aria-valuetext="100%"/);
        assert.ok(html.includes(zoom));
        assert.match(html, new RegExp(`<button[^>]*disabled=""[^>]*>${confirm}</button>`));
    });
}

test("ingredient cropping reuses the cropper with a square frame and ingredient labels", () => {
    setLocale("en");
    const html = renderToStaticMarkup(createElement(Cropper, {
        source: "/ingredient.jpg", title: "ครอปรูปวัตถุดิบ", imageLabel: "รูปวัตถุดิบ", cropShape: "rect",
    }));
    assert.ok(html.includes("Crop ingredient picture"));
    assert.match(html, /aria-label="Ingredient picture"/);
    assert.match(html, /data-crop-shape="rect"/);
    assert.doesNotMatch(html, /profile/i);
});
