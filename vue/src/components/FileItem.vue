<script setup lang="ts">
import { FileOutlined, FolderOpenOutlined, EllipsisOutlined, HeartOutlined, HeartFilled } from '@/icon'
import { useGlobalStore } from '@/store/useGlobalStore'
import { fallbackImage, ok } from 'vue3-ts-util'
import type { FileNodeInfo } from '@/api/files'
import { isImageFile, isVideoFile, isAudioFile } from '@/util'
import { toImageThumbnailUrl, toVideoCoverUrl, toRawFileUrl } from '@/util/file'
import type { MenuInfo } from 'ant-design-vue/lib/menu/src/interface'
import { computed, ref } from 'vue'
import ContextMenu from './ContextMenu.vue'
import ChangeIndicator from './ChangeIndicator.vue'
import { useTagStore } from '@/store/useTagStore'
import { CloseCircleOutlined, StarFilled, StarOutlined } from '@/icon'
import { Tag } from '@/api/db'
import { openVideoModal, openAudioModal } from './functionalCallableComp'
import type { GenDiffInfo } from '@/api/files'
import { play } from '@/icon'
import { Top4MediaInfo, FolderStatsInfo } from '@/api'
import { watch } from 'vue'
import { debounce } from 'lodash-es'

import { closeImageFullscreenPreview } from '@/util/imagePreviewOperation'

const global = useGlobalStore()
const tagStore = useTagStore()

const props = withDefaults(
  defineProps<{
    file: FileNodeInfo,
    idx: number
    selected?: boolean
    showMenuIdx?: number
    cellWidth: number
    fullScreenPreviewImageUrl?: string
    enableRightClickMenu?: boolean,
    enableCloseIcon?: boolean,
    isSelectedMutilFiles?: boolean
    genInfo?: string
    enableChangeIndicator?: boolean
    extraTags?: Tag[]
    coverFiles?: Top4MediaInfo[]
    folderStats?: FolderStatsInfo
    getGenDiff?: (ownGenInfo: any, idx: any, increment: any, ownFile: FileNodeInfo) => GenDiffInfo,
    getGenDiffWatchDep?: (idx: number) => any
  }>(),
  {
    selected: false, enableRightClickMenu: true, enableCloseIcon: false
  }
)


const genDiffToPrevious = ref<GenDiffInfo>()
const genDiffToNext = ref<GenDiffInfo>()
const calcGenInfoDiff = debounce(() => {
  const { getGenDiff, file, idx } = props
  if (!getGenDiff) return 
  genDiffToNext.value = getGenDiff(file.gen_info_obj, idx, 1, file)
  genDiffToPrevious.value = getGenDiff(file.gen_info_obj, idx, -1, file)
}, 200 + 100 * Math.random())

watch(() => props.getGenDiffWatchDep?.(props.idx), () => {
  calcGenInfoDiff()
}, { immediate: true, deep: true })

const emit = defineEmits<{
  'update:showMenuIdx': [v: number],
  'fileItemClick': [event: MouseEvent, file: FileNodeInfo, idx: number],
  'dragstart': [event: DragEvent, idx: number],
  'dragend': [event: DragEvent, idx: number],
  'previewVisibleChange': [value: boolean, last: boolean],
  'contextMenuClick': [e: MenuInfo, file: FileNodeInfo, idx: number],
  'close-icon-click': [],
  'tiktokView': [file: FileNodeInfo, idx: number]
}>()

const customTags = computed(() => {
  return tagStore.tagMap.get(props.file.fullpath) ?? []
})

const imageSrc = computed(() => {
  const r = global.gridThumbnailResolution
  return global.enableThumbnail ? toImageThumbnailUrl(props.file, [r, r].join('x')) : toRawFileUrl(props.file)
})

const tags = computed(() => {
  return (global.conf?.all_custom_tags ?? []).reduce((p, c) => {
    return [...p, { ...c, selected: !!customTags.value.find((v) => v.id === c.id) }]
  }, [] as (Tag & { selected: boolean })[])
})

const likeTag = computed(() => tags.value.find(v => v.type === 'custom' && v.name === 'like'))

const taggleLikeTag = () => {
  ok(likeTag.value)
  emit('contextMenuClick', { key: `toggle-tag-${likeTag.value.id}` } as MenuInfo, props.file, props.idx)
}

const formatShortDateTime = (dateStr: string) => {
  // Various input formats to yy-mm-dd hh:mm
  // "2025-12-28 15:30:45" -> "25-12-28 15:30"
  // "28.12.2025 15:30:45" -> "25-12-28 15:30"
  
  // Try ISO format first (yyyy-mm-dd hh:mm:ss)
  let match = dateStr.match(/(\d{4})-(\d{2})-(\d{2})\s(\d{2}:\d{2})/)  
  if (match) {
    const year = match[1].slice(-2) // Last 2 digits
    return `${year}-${match[2]}-${match[3]} ${match[4]}`
  }
  
  // Try European format (dd.mm.yyyy hh:mm:ss)
  match = dateStr.match(/(\d{2})\.(\d{2})\.(\d{4})\s(\d{2}:\d{2})/)
  if (match) {
    const year = match[3].slice(-2) // Last 2 digits
    return `${year}-${match[2]}-${match[1]} ${match[4]}`
  }
  
  return dateStr
}

const minShowDetailWidth = 160

// 处理文件点击事件
const handleFileClick = (event: MouseEvent) => {
  // 检查magic switch是否开启且是图片文件（视频有自己的处理逻辑）
  if (global.magicSwitchTiktokView && props.file.type === 'file' && isImageFile(props.file.name)) {
    // 阻止事件传播，防止 a-image 组件也触发预览
    event.stopPropagation()
    event.preventDefault()
    // 直接触发TikTok视图
    emit('tiktokView', props.file, props.idx)
    setTimeout(() => {
      closeImageFullscreenPreview()
    }, 500);
  } else {
    // 正常触发文件点击事件
    emit('fileItemClick', event, props.file, props.idx)
  }
}

// 处理视频点击事件
const handleVideoClick = () => {
  if (global.magicSwitchTiktokView) {
    // 直接触发TikTok视图
    emit('tiktokView', props.file, props.idx)
  } else {
    // 正常打开视频模态框
    openVideoModal(
      props.file, 
      (id) => emit('contextMenuClick', { key: `toggle-tag-${id}` } as any, props.file, props.idx),
      () => emit('tiktokView', props.file, props.idx)
    )
  }
}

// 处理音频点击事件
const handleAudioClick = () => {
  if (global.magicSwitchTiktokView) {
    // 直接触发TikTok视图
    emit('tiktokView', props.file, props.idx)
  } else {
    // 正常打开音频模态框
    openAudioModal(
      props.file, 
      (id) => emit('contextMenuClick', { key: `toggle-tag-${id}` } as any, props.file, props.idx),
      () => emit('tiktokView', props.file, props.idx)
    )
  }
}
</script>
<template>
  <a-dropdown :trigger="['contextmenu']" :visible="!global.longPressOpenContextMenu ? undefined : typeof idx === 'number' && showMenuIdx === idx
    " @update:visible="(v: boolean) => typeof idx === 'number' && emit('update:showMenuIdx', v ? idx : -1)">
    <li class="file file-item-trigger grid" :class="{
    clickable: file.type === 'dir',
    selected
  }" :data-idx="idx" :key="file.name" draggable="true" @dragstart="emit('dragstart', $event, idx)"
      @dragend="emit('dragend', $event, idx)" @click.capture="handleFileClick($event)">

      <div>
        <div class="close-icon" v-if="enableCloseIcon" @click="emit('close-icon-click')">
          <close-circle-outlined />
        </div>
        <div class="more" v-if="enableRightClickMenu">
          <a-dropdown>
            <div class="float-btn-wrap">
              <ellipsis-outlined />
            </div>
            <template #overlay>
              <context-menu :file="file" :idx="idx" :selected-tag="customTags"
                @context-menu-click="(e, f, i) => emit('contextMenuClick', e, f, i)"
                :is-selected-mutil-files="isSelectedMutilFiles" />
            </template>
          </a-dropdown>
          <a-dropdown v-if="file.type === 'file'">
            <div class="float-btn-wrap" :class="{ 'like-selected': likeTag?.selected }" @click="taggleLikeTag">
              <HeartFilled v-if="likeTag?.selected" />
              <HeartOutlined v-else />
            </div>
            <template #overlay>
              <a-menu @click="emit('contextMenuClick', $event, file, idx)" v-if="tags.length > 1">
                <a-menu-item v-for="tag in tags" :key="`toggle-tag-${tag.id}`">{{ tag.name }}
                  <star-filled v-if="tag.selected" /><star-outlined v-else />
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
        <!-- :key="fullScreenPreviewImageUrl ? undefined : file.fullpath" 
          这么复杂是因为再全屏查看时可能因为直接删除导致fullpath变化，然后整个预览直接退出-->
        <div :key="file.fullpath" :class="`idx-${idx} item-content`" v-if="isImageFile(file.name)">

          <!-- change indicators -->
          <ChangeIndicator v-if="enableChangeIndicator && genDiffToNext && genDiffToPrevious"
            :gen-diff-to-next="genDiffToNext" :gen-diff-to-previous="genDiffToPrevious" />
          <!-- change indicators END -->

          <a-image :src="imageSrc" :fallback="fallbackImage" :preview="{
    src: fullScreenPreviewImageUrl,
    onVisibleChange: (v: boolean, lv: boolean) => emit('previewVisibleChange', v, lv)
  }" />
          <div class="tags-container" v-if="customTags && cellWidth > minShowDetailWidth">
            <a-tag v-for="tag in extraTags ?? customTags" :key="tag.id" :color="tagStore.getColor(tag)">
              {{ tag.name }}
            </a-tag>
          </div>
        </div>
        <div :class="`idx-${idx} item-content video`" :url="toVideoCoverUrl(file)"
          :style="{ 'background-image': `url('${file.cover_url ?? toVideoCoverUrl(file)}')` }" v-else-if="isVideoFile(file.name)"
          @click="handleVideoClick">

          <div class="play-icon">
            <img :src="play" style="width: 40px;height: 40px;">
          </div>
          <div class="tags-container" v-if="customTags && cellWidth > minShowDetailWidth">
            <a-tag v-for="tag in customTags" :key="tag.id" :color="tagStore.getColor(tag)">
              {{ tag.name }}
            </a-tag>
          </div>
        </div>
        <div :class="`idx-${idx} item-content audio`" v-else-if="isAudioFile(file.name)"
          @click="handleAudioClick">
          <div class="audio-icon">🎵</div>
          <div class="tags-container" v-if="customTags && cellWidth > minShowDetailWidth">
            <a-tag v-for="tag in customTags" :key="tag.id" :color="tagStore.getColor(tag)">
              {{ tag.name }}
            </a-tag>
          </div>
        </div>
        <div v-else class="preview-icon-wrap">
          <file-outlined class="icon center" v-if="file.type === 'file'" />
          <div v-else-if="coverFiles?.length && cellWidth > 160" class="dir-cover-container">
            <img class="dir-cover-item"
              :src="item.media_type === 'image' ? toImageThumbnailUrl(item) : toVideoCoverUrl(item)"
              v-for="item in coverFiles" :key="item.fullpath">
          </div>

          <folder-open-outlined class="icon center" v-else />
          
          <!-- Folder Stats Overlay - only show if we have tags or words -->
          <div v-if="file.type === 'dir' && folderStats && (folderStats.top_tags?.length || folderStats.prompt_analysis?.top_words?.length)" 
               class="folder-stats-overlay">
            <div class="stats-section" v-if="folderStats.top_tags?.length">
              <div class="stats-title">🏷️ Top Tags</div>
              <div class="stats-items">
                <span v-for="tag in folderStats.top_tags.slice(0, 3)" 
                      :key="tag.tag_name" 
                      class="stats-tag">
                  {{ tag.tag_name }} <small>({{ tag.count }})</small>
                </span>
              </div>
            </div>
            
            <div class="stats-section" v-if="folderStats.prompt_analysis?.top_words?.length">
              <div class="stats-title">📝 Top Words</div>
              <div class="stats-items">
                <span v-for="word in folderStats.prompt_analysis.top_words.slice(0, 3)" 
                      :key="word.word" 
                      class="stats-word">
                  {{ word.word }} <small>({{ word.count }})</small>
                </span>
              </div>
            </div>
          </div>
        </div>
        <div class="profile" v-if="cellWidth > minShowDetailWidth">
          <div class="name line-clamp-1" :title="file.name">
            {{ file.name }}
          </div>
          <div class="basic-info">
            <div style="margin-right: 4px;">
              <!-- For folders: Compact statistics -->
              <template v-if="file.type === 'dir' && folderStats">
                <!-- 📄{{ folderStats.file_count }} -->
                <!-- Use media_file_count for total media, or fallback to indexed stats -->
                <template v-if="folderStats.media_file_count > 0">
                  🖼️{{ folderStats.media_file_count }}
                </template>
                <template v-else-if="folderStats.media_stats?.indexed_media > 0">
                  🖼️{{ folderStats.media_stats.indexed_media }}
                </template>
                <!-- Show tagged count if we have indexed images -->
                <template v-if="folderStats.media_stats?.indexed_media > 0 && folderStats.media_stats?.tagged_images > 0">
                  🏷️{{ folderStats.media_stats.tagged_images }}
                </template>
                <template v-if="folderStats.subfolder_count > 0">
                  📁{{ folderStats.subfolder_count }}
                </template>
              </template>
              <!-- For folders without stats -->
              <template v-else-if="file.type === 'dir' && !folderStats">
                {{ file.type }} {{ file.size }}
              </template>
              <!-- For files -->
              <template v-else>
                {{ file.type }} {{ file.size }}
              </template>
            </div>
            <div>
              <!-- Date/Time in short form for folders -->
              <template v-if="file.type === 'dir'">
                {{ formatShortDateTime(file.date) }}
              </template>
              <template v-else>
                {{ file.date }}
              </template>
            </div>
          </div>
        </div>
      </div>
    </li>
    <template #overlay>
      <context-menu :file="file" :idx="idx" :selected-tag="customTags" v-if="enableRightClickMenu"
        @context-menu-click="(e, f, i) => emit('contextMenuClick', e, f, i)"
        :is-selected-mutil-files="isSelectedMutilFiles" />
    </template>
  </a-dropdown>
</template>
<style lang="scss" scoped>
.center {
  display: flex;
  justify-content: center;
  align-items: center;
}

.item-content {
  position: relative;

  &.video {
    background-color: var(--zp-border);
    border-radius: 8px;
    overflow: hidden;
    width: v-bind('$props.cellWidth + "px"');
    height: v-bind('$props.cellWidth + "px"');
    background-size: cover;
    background-position: center;
    cursor: pointer;
  }

  &.audio {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 8px;
    overflow: hidden;
    width: v-bind('$props.cellWidth + "px"');
    height: v-bind('$props.cellWidth + "px"');
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    
    .audio-icon {
      font-size: 48px;
    }
  }

  .play-icon {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    border-radius: 100%;
    display: flex;
  }

  .tags-container {
    position: absolute;
    right: 8px;
    bottom: 8px;
    display: flex;
    width: calc(100% - 16px);
    flex-wrap: wrap-reverse;
    flex-direction: row-reverse;

    &>* {
      margin: 0 0 4px 4px;
      font-size: 14px;
      line-height: 1.6;
    }
  }
}



.close-icon {
  position: absolute;
  top: 0;
  right: 0;
  transform: translate(50%, -50%) scale(1.5);
  cursor: pointer;
  z-index: 100;
  border-radius: 100%;
  overflow: hidden;
  line-height: 1;
  background-color: var(--zp-primary-background);
}

.file {
  padding: 8px 16px;
  margin: 8px;
  display: flex;
  align-items: center;
  background: var(--zp-primary-background);
  border-radius: 8px;
  box-shadow: 0 0 4px var(--zp-secondary-variant-background);
  position: relative;

  &:hover .more {
    opacity: 1;
  }

  .more {
    opacity: 0;
    transition: all 0.3s ease;
    position: absolute;
    top: 4px;
    right: 4px;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    line-height: 1em;

    .float-btn-wrap {
      font-size: 1.5em;
      cursor: pointer;
      font-size: 500;
      padding: 4px;
      border-radius: 100vh;
      color: white;
      background: var(--zp-icon-bg);

      margin-bottom: 4px;

      &.like-selected {
        color: rgb(223, 5, 5);
      }
    }
  }

  &.grid {
    padding: 0;
    display: inline-block;
    box-sizing: content-box;
    box-shadow: unset;

    background-color: var(--zp-secondary-background);

    :deep() {
      .icon {
        font-size: 8em;
      }

      .profile {
        padding: 0 4px;

        .name {
          font-weight: 500;
          padding: 0;
        }

        .basic-info {
          display: flex;
          justify-content: space-between;
          flex-direction: row;
          margin: 0;
          font-size: 0.7em;
          line-height: 1.4;
          
          * {
            white-space: nowrap;
            overflow: hidden;
          }
          
          > div:first-child {
            display: flex;
            gap: 3px;
            align-items: center;
          }
        }
      }

      .ant-image,
      .preview-icon-wrap {
        border: 1px solid var(--zp-secondary);
        background-color: var(--zp-secondary-variant-background);
        border-radius: 8px;
        overflow: hidden;
      }

      img:not(.dir-cover-item),
      .dir-cover-container,
      .preview-icon-wrap>[role='img'] {
        height: v-bind('$props.cellWidth + "px"');
        width: v-bind('$props.cellWidth + "px"');
        object-fit: contain;
      }
    }
  }


  &.clickable {
    cursor: pointer;
  }

  &.selected {
    outline: #0084ff solid 2px;
  }

  .name {
    flex: 1;
    padding: 8px;
    word-break: break-all;
  }

  .basic-info {
    overflow: hidden;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
  }

  .dir-cover-container {
    top: 0;
    display: flex;
    flex-wrap: wrap;
    padding: 4px;

    &>img {
      width: calc(50% - 8px);
      height: calc(50% - 8px);
      margin: 4px;
      object-fit: cover;
      border-radius: 8px;
      overflow: hidden
    }
  }
}

.folder-stats-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
  opacity: 0;
  transition: opacity 0.2s ease 0.1s;
  padding: 16px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  pointer-events: none;
  z-index: 50;
  
  .stats-section {
    .stats-title {
      font-size: 0.9em;
      font-weight: 600;
      margin-bottom: 6px;
      color: #fff;
    }
    
    .stats-items {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      
      span {
        background: var(--zp-primary-background);
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.85em;
        color: var(--zp-primary);
        
        small {
          opacity: 0.7;
          margin-left: 4px;
        }
      }
      
      .stats-tag {
        border: 1px solid var(--zp-secondary);
      }
      
      .stats-word {
        border: 1px solid var(--zp-border);
      }
    }
  }
}

.preview-icon-wrap:hover .folder-stats-overlay {
  opacity: 1;
}
</style>
