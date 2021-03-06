# 进行人脸录入 / face register
# 录入多张人脸 / support multi-faces

# Author:   coneypo
# Blog:     http://www.cnblogs.com/AdaminXie
# GitHub:   https://github.com/coneypo/Dlib_face_recognition_from_camera
# Mail:     coneypo@foxmail.com


import dlib
import numpy as np
import cv2
import os
import shutil
import pandas as pd
import time
from PIL import Image, ImageDraw, ImageFont

# Dlib 正向人脸检测器
detector = dlib.get_frontal_face_detector()

# 2. Dlib 人脸 landmark 特征点检测器
predictor = dlib.shape_predictor('data/data_dlib/shape_predictor_68_face_landmarks.dat')

# 3. Dlib Resnet 人脸识别模型，提取 128D 的特征矢量
face_reco_model = dlib.face_recognition_model_v1("data/data_dlib/dlib_face_recognition_resnet_model_v1.dat")


class Face_Register:
    def __init__(self):
        self.font = cv2.FONT_ITALIC

        # for FPS
        self.frame_time = 0
        self.frame_start_time = 0
        self.fps = 0

        # list to save centroid positions of ROI in frame N-1 and N
        self.last_frame_centroid_list = []
        self.current_frame_centroid_list = []

        # list to save names of ROI in frame N-1 and N
        self.last_frame_names_list = []
        self.current_frame_face_names_list = []

        # cnt for faces in frame N-1 and N
        self.last_frame_faces_cnt = 0
        self.current_frame_faces_cnt = 0

        # 用来存放所有录入人脸特征的数组 / Save the features of faces in the database
        self.features_known_list = []

        self.e_distance_list = []

        # 存储录入人脸名字 / Save the name of faces known
        self.name_known_cnt = 0
        self.name_known_list = []

        # 存储当前摄像头中捕获到的所有人脸的坐标名字 / Save the positions and names of current faces captured
        self.current_frame_face_pos_list = []
        # 存储当前摄像头中捕获到的人脸特征
        self.current_frame_face_features_list = []

    def get_face_database(self):
        if os.path.exists("data/features_all.csv"):
            path_features_known_csv = "data/features_all.csv"
            csv_rd = pd.read_csv(path_features_known_csv, header=None)
            # 2. 读取已知人脸数据 / Print known faces
            for i in range(csv_rd.shape[0]):
                features_someone_arr = []
                for j in range(0, 128):
                    if csv_rd.iloc[i][j] == '':
                        features_someone_arr.append('0')
                    else:
                        features_someone_arr.append(csv_rd.iloc[i][j])
                self.features_known_list.append(features_someone_arr)
                self.name_known_list.append("Person_" + str(i + 1))
            self.name_known_cnt = len(self.name_known_list)
            print("Faces in Database：", len(self.features_known_list))
            return 1
        else:
            print('##### Warning #####', '\n')
            print("'features_all.csv' not found!")
            print(
                "Please run 'get_faces_from_camera.py' and 'features_extraction_to_csv.py' before 'face_reco_from_camera.py'",
                '\n')
            print('##### End Warning #####')
            return 0

        # 计算两个128D向量间的欧式距离 / Compute the e-distance between two 128D features

    # 获取处理之后 stream 的帧数 / Get the fps of video stream
    def update_fps(self):
        now = time.time()
        self.frame_time = now - self.frame_start_time
        self.fps = 1.0 / self.frame_time
        self.frame_start_time = now
        # 计算两个128D向量间的欧式距离 / Compute the e-distance between two 128D features

    @staticmethod
    def return_euclidean_distance(feature_1, feature_2):
        feature_1 = np.array(feature_1)
        feature_2 = np.array(feature_2)
        dist = np.sqrt(np.sum(np.square(feature_1 - feature_2)))
        return dist

    # 生成的 cv2 window 上面添加说明文字 / putText on cv2 window
    def draw_note(self, img_rd):
        # 添加说明 / Add some statements
        cv2.putText(img_rd, "Face Recognizer with OT (one person)", (20, 40), self.font, 1, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(img_rd, "FPS:   " + str(self.fps.__round__(2)), (20, 100), self.font, 0.8, (0, 255, 0), 1,
                    cv2.LINE_AA)
        cv2.putText(img_rd, "Q: Quit", (20, 450), self.font, 0.8, (255, 255, 255), 1, cv2.LINE_AA)

    # 获取人脸
    def process(self, stream):
        # 1. read data of known faces from csv
        if self.get_face_database():
            while stream.isOpened():
                print(">>>>>>>>>>> Frame X starts...")
                flag, img_rd = stream.read()
                kk = cv2.waitKey(1)
                # 2. detect faces for frame X
                faces = detector(img_rd, 0)

                # 3. update cnt for faces in frames
                self.last_frame_faces_cnt = self.current_frame_faces_cnt
                self.current_frame_faces_cnt = len(faces)
                print("     >>>>>> current_frame_faces_cnt:                      ", self.current_frame_faces_cnt)

                # 4. if cnt not changes, 1->1 or 0->0
                if self.current_frame_faces_cnt == self.last_frame_faces_cnt:
                    print("     >>>>>> scene 1: no faces cnt changes in this frame!!!")
                    # one face in this frame
                    if self.current_frame_faces_cnt != 0:
                        # 4.1 get ROI positions
                        for k, d in enumerate(faces):
                            # 计算矩形框大小 / Compute the size of rectangle box
                            height = (d.bottom() - d.top())
                            width = (d.right() - d.left())
                            hh = int(height / 2)
                            ww = int(width / 2)

                            cv2.rectangle(img_rd,
                                          tuple([d.left() - ww, d.top() - hh]),
                                          tuple([d.right() + ww, d.bottom() + hh]),
                                          (255, 255, 255), 2)

                            self.current_frame_face_pos_list[k] = tuple(
                                [faces[k].left(), int(faces[k].bottom() + (faces[k].bottom() - faces[k].top()) / 4)])

                            print("     >>>>>> self.current_frame_face_names_list[k]:        ",
                                  self.current_frame_face_names_list[k])
                            print("     >>>>>> self.current_frame_face_pos_list[k]:          ",
                                  self.current_frame_face_pos_list[k])

                            # 4.2 write names under ROI
                            cv2.putText(img_rd, self.current_frame_face_names_list[k],
                                        self.current_frame_face_pos_list[k], self.font, 0.8, (0, 255, 255), 1,
                                        cv2.LINE_AA)

                # 5. if cnt of faces changes, 0->1 or 1->0
                else:
                    print("     >>>>>> scene 2: faces cnt changes in this frame")
                    self.current_frame_face_pos_list = []
                    self.e_distance_list = []

                    # 5.1 face cnt: 1->0, no faces in this frame
                    if self.current_frame_faces_cnt == 0:
                        print("     >>>>>> scene 2.1 no guy in this frame!!!")
                        # clear list of names and
                        self.current_frame_face_names_list = []
                        self.current_frame_face_features_list = []

                    # 5.1 face cnt: 0->1, get the new face
                    elif self.current_frame_faces_cnt == 1:
                        print("     >>>>>> scene 2.2 first guy in this frame!!!")
                        self.current_frame_face_names_list = []

                        for i in range(len(faces)):
                            shape = predictor(img_rd, faces[i])
                            self.current_frame_face_features_list.append(
                                face_reco_model.compute_face_descriptor(img_rd, shape))

                        # 5.1.1 遍历捕获到的图像中所有的人脸 / Traversal all the faces in the database
                        for k in range(len(faces)):
                            self.current_frame_face_names_list.append("unknown")

                            # 每个捕获人脸的名字坐标 / Positions of faces captured
                            self.current_frame_face_pos_list.append(tuple(
                                [faces[k].left(), int(faces[k].bottom() + (faces[k].bottom() - faces[k].top()) / 4)]))
                            print("     >>>>>> self.current_frame_face_features_list:         ",
                                  self.current_frame_face_features_list)
                            # 5.1.2 对于某张人脸，遍历所有存储的人脸特征
                            # For every faces detected, compare the faces in the database

                            for i in range(len(self.features_known_list)):
                                # 如果 person_X 数据不为空
                                if str(self.features_known_list[i][0]) != '0.0':
                                    print("     >>>>>> with person", str(i + 1), "the e distance:                   ", end='')
                                    e_distance_tmp = self.return_euclidean_distance(
                                        self.current_frame_face_features_list[k],
                                        self.features_known_list[i])
                                    print(e_distance_tmp)
                                    self.e_distance_list.append(e_distance_tmp)
                                else:
                                    # 空数据 person_X
                                    self.e_distance_list.append(999999999)

                            # 5.1.3. 寻找出最小的欧式距离匹配 / Find the one with minimum e distance
                            similar_person_num = self.e_distance_list.index(min(self.e_distance_list))

                            if min(self.e_distance_list) < 0.4:
                                self.current_frame_face_names_list[k] = self.name_known_list[similar_person_num]
                            else:
                                print("     >>>>>> Unknown person")

                # 9. 生成的窗口添加说明文字 / Add note on cv2 window
                self.draw_note(img_rd)

                # 10. 按下 'q' 键退出 / Press 'q' to exit
                if kk == ord('q'):
                    break

                self.update_fps()
                cv2.namedWindow("camera", 1)
                cv2.imshow("camera", img_rd)

                print(">>>>>>>>>>> Frame X ends...\n\n")

    def run(self):
        # cap = cv2.VideoCapture("head-pose-face-detection-female-and-male.mp4")
        cap = cv2.VideoCapture(0)
        self.process(cap)

        cap.release()
        cv2.destroyAllWindows()


def main():
    Face_Register_con = Face_Register()
    Face_Register_con.run()


if __name__ == '__main__':
    main()
