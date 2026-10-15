import { useState } from "react";

export default function NotificationImage(props) {
    const { image, Icon } = props;
    const [failedImage, setFailedImage] = useState(null);
    // Existing ingredient placeholders are not ingredient photos.
    const hasPhoto = image && !/no-image-available/i.test(image) && failedImage !== image;
    return hasPhoto
        ? <img src={image} alt="" className="w-full h-full rounded-full object-cover" onError={() => setFailedImage(image)} />
        : <Icon className="w-5 h-5" aria-hidden="true" />;
}
