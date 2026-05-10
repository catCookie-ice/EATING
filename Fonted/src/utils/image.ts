import imageCompression from 'browser-image-compression'

const MAX_SIZE = 5 * 1024 * 1024 // 5MB

/**
 * 校验图片并压缩
 *
 * 规则：
 *  1. 检查是否为图片
 *  2. 原始大小超过 5MB 则拒绝上传
 *  3. 压缩图片
 *  4. 压缩后仍超过 5MB 则拒绝
 *
 * @returns 压缩后的 File
 */
export async function compressImage(file: File): Promise<File> {
  // 1. 检查是否为图片
  if (!file.type.startsWith('image/')) {
    throw new Error('请选择图片文件')
  }

  // 2. 检查原始大小
  if (file.size > MAX_SIZE) {
    throw new Error('图片原始大小超过 5MB，不允许上传')
  }

  // 3. 执行压缩
  let compressed: File
  try {
    compressed = await imageCompression(file, {
      maxSizeMB: 5,
      maxWidthOrHeight: 1920,
      useWebWorker: true,
      fileType: file.type,
    })
  } catch {
    throw new Error('图片压缩失败，请重试')
  }

  // 4. 检查压缩后大小
  if (compressed.size > MAX_SIZE) {
    throw new Error('图片压缩后超过 5MB，等等！不对！你是怎么传上来的')
  }

  return compressed
}
