import box from './assets/truck-box.jpg'
import reefer from './assets/truck-reefer.jpg'
import van from './assets/truck-van.jpg'

// 按车型名映射车辆图片
export const truckImage = (model = '') =>
  model.includes('冷藏') ? reefer
    : model.includes('依维柯') || model.includes('面包') ? van
      : box
